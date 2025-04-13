from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from datetime import datetime
import jwt
from flask import current_app
import logging
from .user_system import db, User, TokenBlacklist  # 添加导入

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理员权限检查装饰器
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 从请求头获取令牌
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "缺少认证令牌"}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # 解码令牌 - 使用与auth_routes.py相同的密钥获取逻辑
            # 获取密钥，确保与登录时使用的相同
            secret_key = current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY', 'dev_key_please_change')
            if not isinstance(secret_key, str):
                secret_key = str(secret_key)  # 转换为字符串
            
            # 解码令牌
            data = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # 使用 SQLAlchemy 查询用户
            user = User.query.filter_by(public_id=data['public_id']).first()
            
            if not user:
                return jsonify({"message": "用户未找到"}), 404
                
            if not user.is_admin:
                return jsonify({"message": "需要管理员权限"}), 403
                
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "令牌已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "无效的令牌"}), 401
        except Exception as e:
            return jsonify({"message": f"认证错误: {str(e)}"}), 401
            
    return decorated

# 管理面板首页
@admin_bp.route('/')
@admin_required
def admin_panel():
    # 获取用户统计
    user_count = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    
    # 获取最近注册的用户
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # 获取系统统计
    stats = {
        'user_count': user_count,
        'admin_count': admin_count,
        'recent_users': [u.to_dict() for u in recent_users]
    }
    
    return render_template('admin/index.html', stats=stats)

# 用户管理
@admin_bp.route('/users')
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=[u.to_dict() for u in users])

# 查看单个用户
@admin_bp.route('/users/<int:user_id>')
@admin_required
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/user_detail.html', user=user.to_dict())

# 设置用户为管理员
@admin_bp.route('/users/<int:user_id>/set_admin', methods=['POST'])
@admin_required
def set_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user.is_admin = True
    db.session.commit()
    
    flash(f'用户 {user.username} 已设置为管理员', 'success')
    return redirect(url_for('admin.manage_users'))

# 移除管理员权限
@admin_bp.route('/users/<int:user_id>/remove_admin', methods=['POST'])
@admin_required
def remove_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user.is_admin = False
    db.session.commit()
    
    flash(f'已移除 {user.username} 的管理员权限', 'success')
    return redirect(url_for('admin.manage_users'))

# 删除用户
@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # 检查是否是最后一个管理员
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('不能删除最后一个管理员', 'error')
            return redirect(url_for('admin.manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'用户 {user.username} 已删除', 'success')
    return redirect(url_for('admin.manage_users'))

# 系统日志
@admin_bp.route('/logs')
@admin_required
def view_logs():
    log_type = request.args.get('type', 'access')  # 默认显示access
  
    # 根据类型选择不同的日志文件
    if log_type == 'access':
        log_file = 'logs/gunicorn_access.log'  # Gunicorn访问日志
    elif log_type == 'error':
        log_file = 'logs/gunicorn_error.log'  # Gunicorn错误日志
    else:
        return jsonify({"error": "无效的日志类型"}), 400
    
    logs = []
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()[-100:]  # 获取最后100行
        else:
            # 如果文件不存在，返回提示信息
            return jsonify([f"日志文件 {log_file} 不存在或尚未生成"]), 200
        
        # 返回JSON格式的日志列表
        return jsonify(logs), 200
    except Exception as e:
        logging.error(f"读取日志文件时出错: {str(e)}")
        return jsonify({"error": f"无法读取日志文件: {str(e)}"}), 500

# 系统设置
@admin_bp.route('/settings')
@admin_required
def settings():
    return render_template('admin/settings.html')

# 更新系统设置
@admin_bp.route('/settings/update', methods=['POST'])
@admin_required
def update_settings():
    # 这里可以添加更新系统设置的逻辑
    flash('系统设置已更新', 'success')
    return redirect(url_for('admin.settings'))

# API: 获取用户列表
@admin_bp.route('/api/users')
@admin_required
def api_users():
    users = User.query.order_by(User.created_at.desc()).all()
    
    # 将Row对象转换为字典列表
    user_list = []
    for user in users:
        user_dict = user.to_dict()
        # 确保is_admin是数字1或0，以便前端识别
        if 'is_admin' in user_dict:
            user_dict['role'] = 1 if user_dict['is_admin'] else 0
        user_list.append(user_dict)
    
    return jsonify(user_list)

# API: 获取系统统计
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    # 获取用户统计
    user_count = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    
    # 获取今日注册用户数
    today = datetime.now().strftime('%Y-%m-%d')
    today_users = User.query.filter(User.created_at.like(f'{today}%')).count()
    
    # 获取今日活跃用户数(根据上次登录时间计算)
    active_today = User.query.filter(User.last_login.like(f'{today}%')).count()
    
    # 统计数据
    stats = {
        'user_count': user_count,
        'admin_count': admin_count,
        'today_users': today_users,
        'active_today': active_today
    }
    
    return jsonify(stats)

# 添加管理员登录路由
@admin_bp.route('/login', methods=['GET'])
def admin_login_page():
    """返回管理员登录页面"""
    return send_from_directory('../front_html', 'admin-login.html')

# 获取日志API端点
@admin_bp.route('/api/logs', methods=['GET'])
@admin_required
def api_get_logs():
    """获取系统日志"""
    log_file = 'app.log'
    
    if not os.path.exists(log_file):
        return jsonify({"error": "日志文件不存在"}), 404
    
    try:
        with open(log_file, 'r') as f:
            # 获取最近100行日志
            logs = f.readlines()[-100:]
        
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": f"读取日志失败: {str(e)}"}), 500

# 系统设置API端点
@admin_bp.route('/api/settings', methods=['GET'])
@admin_required
def api_get_settings():
    """获取系统设置"""
    settings = {
        'site_name': os.environ.get('SITE_NAME', 'BioInfo Nexus'),
        'site_description': os.environ.get('SITE_DESCRIPTION', 'BioInfo Nexus是一个生物信息学分析平台。'),
        'admin_email': os.environ.get('ADMIN_EMAIL', 'admin@example.com'),
        'smtp_server': os.environ.get('MAIL_SERVER', ''),
        'smtp_port': os.environ.get('MAIL_PORT', '465'),
    }
    
    return jsonify(settings)

# 更新系统设置API端点
@admin_bp.route('/api/settings/update', methods=['POST'])
@admin_required
def api_update_settings():
    try:
        site_name = request.form.get('siteName', '')
        site_description = request.form.get('siteDescription', '')
        admin_email = request.form.get('adminEmail', '')
        smtp_server = request.form.get('smtpServer', '')
        smtp_port = request.form.get('smtpPort', '')
        
        # 这里可以保存这些设置到数据库或配置文件
        # 现在只记录日志
        logging.info(f"系统设置已更新: 网站名称={site_name}, 管理员邮箱={admin_email}")
        
        return jsonify({"message": "系统设置已更新", "success": True})
    except Exception as e:
        logging.error(f"更新系统设置失败: {str(e)}")
        return jsonify({"error": f"更新系统设置失败: {str(e)}"}), 500

# 设置用户为管理员 API
@admin_bp.route('/api/users/<int:user_id>/set_admin', methods=['POST'])
@admin_required
def api_set_admin(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        user.is_admin = True
        db.session.commit()
        
        logging.info(f"用户 {user.username} (ID: {user_id}) 已被设置为管理员")
        return jsonify({"message": f"用户 {user.username} 已设置为管理员", "success": True})
    
    except Exception as e:
        logging.error(f"设置管理员失败: {str(e)}")
        return jsonify({"error": f"设置管理员失败: {str(e)}"}), 500

# 移除管理员权限 API
@admin_bp.route('/api/users/<int:user_id>/remove_admin', methods=['POST'])
@admin_required
def api_remove_admin(user_id):
    try:
        # 获取当前用户信息
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        current_user_data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        
        current_user = User.query.filter_by(public_id=current_user_data['public_id']).first()
        
        # 检查是否是自己
        if current_user and current_user.id == user_id:
            return jsonify({"error": "不能移除自己的管理员权限"}), 400
        
        user = User.query.get_or_404(user_id)
        
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # 检查是否是最后一个管理员
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({"error": "不能移除最后一个管理员"}), 400
        
        user.is_admin = False
        db.session.commit()
        
        logging.info(f"已移除用户 {user.username} (ID: {user_id}) 的管理员权限")
        return jsonify({"message": f"已移除 {user.username} 的管理员权限", "success": True})
    
    except Exception as e:
        logging.error(f"移除管理员权限失败: {str(e)}")
        return jsonify({"error": f"移除管理员权限失败: {str(e)}"}), 500

# 删除用户 API
@admin_bp.route('/api/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def api_delete_user(user_id):
    try:
        logging.info(f"开始删除用户，ID: {user_id}")
        
        # 检查用户ID是否有效
        if not user_id or user_id <= 0:
            logging.error(f"尝试删除用户失败：无效的用户ID: {user_id}")
            return jsonify({"error": "无效的用户ID"}), 400
        
        # 获取当前用户信息
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        current_user_data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        
        current_user = User.query.filter_by(public_id=current_user_data['public_id']).first()
        
        # 检查是否是自己
        if current_user and current_user.id == user_id:
            return jsonify({"error": "不能删除自己的账户"}), 400
            
        user = User.query.get_or_404(user_id)
        
        if not user:
            return jsonify({"error": "用户不存在"}), 404
            
        username = user.username
        is_admin = user.is_admin
        
        # 检查是否是最后一个管理员
        if is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({"error": "不能删除最后一个管理员"}), 400
        
        # 执行删除
        db.session.delete(user)
        db.session.commit()
        
        logging.info(f"用户 {username} (ID: {user_id}) 已被成功删除")
        return jsonify({"message": f"用户 {username} 已成功删除", "success": True})
    
    except Exception as e:
        logging.error(f"删除用户失败，ID: {user_id}, 错误: {str(e)}")
        return jsonify({"error": f"删除用户失败: {str(e)}"}), 500