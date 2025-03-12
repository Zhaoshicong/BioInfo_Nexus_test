from flask import Blueprint, request, jsonify
from .user_system import db, User, token_required, admin_required

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

# 获取所有用户
@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 分页查询
    users_pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    
    users_data = []
    for user in users_pagination.items:
        user_data = {
            'id': user.public_id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'created_at': user.created_at
        }
        users_data.append(user_data)
    
    return jsonify({
        'users': users_data,
        'total': users_pagination.total,
        'pages': users_pagination.pages,
        'current_page': users_pagination.page
    }), 200

# 获取单个用户详情
@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
@admin_required
def get_user_detail(current_user, user_id):
    """获取用户详情"""
    user = User.query.filter_by(id=user_id).first()
    
    if not user:
        return jsonify({'message': '用户不存在！'}), 404
    
    # 构建用户数据
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'created_at': user.created_at,
        'last_login': user.last_login,
        'is_active': user.is_active,
        'is_admin': user.is_admin
    }
    
    return jsonify(user_data), 200

# 更新用户状态（激活/禁用）
@admin_bp.route('/users/<public_id>/status', methods=['PUT'])
@token_required
@admin_required
def update_user_status(current_user, public_id):
    user = User.query.filter_by(public_id=public_id).first()
    
    if not user:
        return jsonify({'message': '用户不存在！'}), 404
    
    # 防止管理员禁用自己
    if user.id == current_user.id:
        return jsonify({'message': '不能修改自己的状态！'}), 403
    
    data = request.get_json()
    
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
        db.session.commit()
        
        status = '激活' if user.is_active else '禁用'
        return jsonify({'message': f'用户已{status}！'}), 200
    
    return jsonify({'message': '缺少必要参数！'}), 400

# 更新用户管理员权限
@admin_bp.route('/users/<public_id>/admin', methods=['PUT'])
@token_required
@admin_required
def update_admin_status(current_user, public_id):
    user = User.query.filter_by(public_id=public_id).first()
    
    if not user:
        return jsonify({'message': '用户不存在！'}), 404
    
    # 防止管理员移除自己的管理员权限
    if user.id == current_user.id:
        return jsonify({'message': '不能修改自己的管理员状态！'}), 403
    
    data = request.get_json()
    
    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])
        db.session.commit()
        
        status = '授予' if user.is_admin else '移除'
        return jsonify({'message': f'已{status}用户的管理员权限！'}), 200
    
    return jsonify({'message': '缺少必要参数！'}), 400

# 删除用户
@admin_bp.route('/users/<public_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, public_id):
    """删除用户"""
    # 不允许删除自己
    if current_user.public_id == public_id:
        return jsonify({'message': '不能删除自己的账户！'}), 403
    
    user = User.query.filter_by(public_id=public_id).first()
    
    if not user:
        return jsonify({'message': '用户不存在！'}), 404
    
    # 删除用户
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': '用户已删除！'}), 200

# 获取系统统计信息
@admin_bp.route('/stats', methods=['GET'])
@token_required
@admin_required
def get_stats(current_user):
    """获取系统统计信息"""
    # 获取用户总数
    total_users = User.query.count()
    
    # 获取活跃用户数
    active_users = User.query.filter_by(is_active=True).count()
    
    # 获取管理员数量
    admin_count = User.query.filter_by(is_admin=True).count()
    
    # 构建统计数据
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'admin_count': admin_count
    }
    
    return jsonify(stats), 200 