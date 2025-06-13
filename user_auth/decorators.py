from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime, timedelta
from .user_system import User, MembershipLevel, AIUsageRecord, db

def membership_required(level=MembershipLevel.PLUS.value):
    """
    会员等级要求装饰器
    :param level: 要求的最低会员等级 ("plus" 或 "premium")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 验证JWT令牌
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({"message": "用户未找到"}), 404
                
            # 管理员跳过会员检查
            if user.is_admin:
                return f(*args, **kwargs)
                
            # 检查会员状态和等级
            if not user.is_membership_active():
                return jsonify({"message": "您的会员已过期，请续费"}), 403
                
            # 检查会员等级
            if not user.has_membership_level(level):
                if level == MembershipLevel.PREMIUM.value:
                    return jsonify({"message": "此功能需要Premium会员"}), 403
                else:
                    return jsonify({"message": "此功能需要Plus会员或更高等级"}), 403
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def ai_usage_limit_check(f):
    """
    AI使用次数限制装饰器
    不同会员等级的月度限制：
    - 免费用户：25次/月
    - Plus会员：100次/月
    - Premium会员：无限制
    - 管理员：无限制
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 验证JWT令牌
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"message": "用户未找到"}), 404
        
        # 管理员无限制
        if user.is_admin:
            return f(*args, **kwargs)
        
        # 检查当月使用次数
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_usage = AIUsageRecord.query.filter(
            AIUsageRecord.user_id == user.id,
            AIUsageRecord.usage_date >= current_month_start
        ).count()
        
        # 根据会员等级设置限制
        usage_limits = {
            MembershipLevel.FREE.value: 25,
            MembershipLevel.PLUS.value: 100,
            MembershipLevel.PREMIUM.value: -1  # -1表示无限制
        }
        
        user_limit = usage_limits.get(user.membership_level, 25)  # 默认25次
        
        # Premium会员和管理员无限制
        if user_limit == -1:
            return f(*args, **kwargs)
        
        # 检查是否超过限制
        if current_usage >= user_limit:
            membership_info = {
                MembershipLevel.FREE.value: "免费用户每月限制25次AI分析",
                MembershipLevel.PLUS.value: "Plus会员每月限制100次AI分析"
            }
            
            return jsonify({
                "error": "AI分析次数已达月度限制",
                "message": f"您本月已使用{current_usage}次AI分析，{membership_info.get(user.membership_level, '已达到使用限制')}。升级会员可获得更多使用次数。",
                "current_usage": current_usage,
                "monthly_limit": user_limit,
                "membership_level": user.membership_level,
                "upgrade_suggestion": "升级到Premium会员可享受无限次AI分析" if user.membership_level != MembershipLevel.PREMIUM.value else None
            }), 429  # 429 Too Many Requests
        
        # 记录此次使用
        try:
            # 从请求中获取工具名称（如果有）
            tool_name = None
            sequence_length = None
            
            if request.is_json:
                data = request.get_json()
                if data:
                    # 尝试从toolResults中推断工具名称
                    tool_results = data.get('toolResults', {})
                    if tool_results:
                        tool_name = ', '.join(tool_results.keys())
                    
                    # 获取序列长度
                    sequence = data.get('sequence', '')
                    if sequence:
                        sequence_length = len(sequence)
            
            usage_record = AIUsageRecord(
                user_id=user.id,
                tool_name=tool_name,
                sequence_length=sequence_length
            )
            db.session.add(usage_record)
            db.session.commit()
            
            # 执行原函数并返回结果
            return f(*args, **kwargs)
            
        except Exception as e:
            # 记录使用失败不应该阻止AI分析
            print(f"记录AI使用失败: {str(e)}")
            return f(*args, **kwargs)
    
    return decorated_function

# 简便的Plus会员装饰器
def plus_required(f):
    return membership_required(MembershipLevel.PLUS.value)(f)

# 简便的Premium会员装饰器    
def premium_required(f):
    return membership_required(MembershipLevel.PREMIUM.value)(f) 