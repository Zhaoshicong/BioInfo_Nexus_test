from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging
from .user_system import db, User, MembershipLevel
from .decorators import plus_required, premium_required

# 创建蓝图
membership_bp = Blueprint('membership', __name__, url_prefix='/api/membership')

@membership_bp.route('/status', methods=['GET'])
@jwt_required()
def get_membership_status():
    """获取当前用户的会员状态"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"message": "用户未找到"}), 404
            
        # 检查会员状态
        is_active = user.is_membership_active()
        
        # 返回更多详细信息
        return jsonify({
            "membership_level": user.membership_level,
            "is_active": is_active,
            "is_admin": user.is_admin,
            "expiry_date": user.membership_expiry.isoformat() if user.membership_expiry else None,
            "active_status": "活跃" if is_active else "已过期",
            "username": user.username
        })
    except Exception as e:
        logging.error(f"获取会员状态出错: {str(e)}")
        return jsonify({"message": f"服务器错误: {str(e)}"}), 500

@membership_bp.route('/upgrade', methods=['POST'])
@jwt_required()
def upgrade_membership():
    """升级会员（仅用于演示，实际应该集成支付）"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"message": "用户未找到"}), 404
        
    data = request.get_json()
    if not data or "level" not in data:
        return jsonify({"message": "请提供要升级的会员等级"}), 400
        
    level = data["level"].lower()
    
    # 验证会员等级
    if level not in [MembershipLevel.PLUS.value, MembershipLevel.PREMIUM.value]:
        return jsonify({"message": "无效的会员等级"}), 400
        
    # 设置会员等级和到期时间（30天后）
    user.membership_level = level
    user.membership_expiry = datetime.utcnow() + timedelta(days=30)
    
    # 在实际应用中，这里应该处理支付逻辑
    
    try:
        db.session.commit()
        return jsonify({
            "message": f"会员已升级为{level}",
            "membership_level": user.membership_level,
            "expiry_date": user.membership_expiry.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"会员升级失败: {str(e)}")
        return jsonify({"message": "会员升级失败"}), 500

# 演示Plus会员功能
@membership_bp.route('/plus-feature', methods=['GET'])
@jwt_required()
@plus_required
def plus_feature():
    """Plus会员功能示例"""
    return jsonify({"message": "这是Plus会员的专享功能"})

# 演示Premium会员功能
@membership_bp.route('/premium-feature', methods=['GET'])
@jwt_required()
@premium_required
def premium_feature():
    """Premium会员功能示例"""
    return jsonify({"message": "这是Premium会员的高级功能"}) 