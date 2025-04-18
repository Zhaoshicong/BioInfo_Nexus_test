from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from .user_system import User, MembershipLevel

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

# 简便的Plus会员装饰器
def plus_required(f):
    return membership_required(MembershipLevel.PLUS.value)(f)

# 简便的Premium会员装饰器    
def premium_required(f):
    return membership_required(MembershipLevel.PREMIUM.value)(f) 