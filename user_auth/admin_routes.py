from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from datetime import datetime
import jwt
from flask import current_app
import logging
import pymysql
from dotenv import load_dotenv
from user_auth.user_system import db

# 加载环境变量
load_dotenv()

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 数据库连接函数
def get_db_connection():
    # 从环境变量获取数据库配置
    db_host = os.environ.get('MYSQL_HOST', 'localhost')
    db_user = os.environ.get('MYSQL_USER', 'root') 
    db_password = os.environ.get('MYSQL_PASSWORD', '123456')
    db_name = os.environ.get('MYSQL_DB', 'bioinfo_nexus')
    db_port = int(os.environ.get('MYSQL_PORT', 3306))
    
    # 创建MySQL连接
    conn = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        port=db_port,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

# 管理员权限检查装饰器
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # 使用flask_jwt_extended获取当前用户ID
            current_user_id = get_jwt_identity()
            
            # 从user_auth/user_system.py导入User模型
            from user_auth.user_system import User
            
            # 查询用户
            user = User.query.filter_by(id=current_user_id).first()
            
            if not user:
                return jsonify({"message": "用户未找到"}), 404
                
            if not user.is_admin:
                return jsonify({"message": "需要管理员权限"}), 403
                
            # 传递用户对象给被装饰的函数
            return f(user, *args, **kwargs)
            
        except Exception as e:
            return jsonify({"message": f"认证错误: {str(e)}"}), 401
            
    return decorated

# 管理面板首页
@admin_bp.route('/')
@admin_required
def admin_panel(user):
    conn = get_db_connection()
    
    # 使用User模型查询
    from user_auth.user_system import User
    
    # 获取用户统计
    user_count = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    
    # 获取最近注册的用户
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, created_at as registered_on FROM users ORDER BY created_at DESC LIMIT 5')
    recent_users = cursor.fetchall()
    
    # 获取系统统计
    stats = {
        'user_count': user_count,
        'admin_count': admin_count,
        'recent_users': [dict(u) for u in recent_users]
    }
    
    conn.close()
    return render_template('admin/index.html', stats=stats)

# 用户管理
@admin_bp.route('/users')
@admin_required
def manage_users(user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/users.html', users=users)

# 查看单个用户
@admin_bp.route('/users/<int:user_id>')
@admin_required
def view_user(user, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users', user=user))
    
    return render_template('admin/user_detail.html', user=user)

# 设置用户为管理员
@admin_bp.route('/users/<int:user_id>/set_admin', methods=['POST'])
@admin_required
def set_admin(user, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users', user=user))
    
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_admin = 1 WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'用户 {user["username"]} 已设置为管理员', 'success')
    return redirect(url_for('admin.manage_users', user=user))

# 移除管理员权限
@admin_bp.route('/users/<int:user_id>/remove_admin', methods=['POST'])
@admin_required
def remove_admin(user, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users', user=user))
    
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_admin = 0 WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'已移除 {user["username"]} 的管理员权限', 'success')
    return redirect(url_for('admin.manage_users', user=user))

# 删除用户
@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users', user=user))
    
    # 检查是否是最后一个管理员
    if user['is_admin']:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_count = cursor.fetchone()['COUNT(*)']
        if admin_count <= 1:
            conn.close()
            flash('不能删除最后一个管理员', 'error')
            return redirect(url_for('admin.manage_users', user=user))
    
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'用户 {user["username"]} 已删除', 'success')
    return redirect(url_for('admin.manage_users', user=user))

# 系统日志
@admin_bp.route('/logs')
@jwt_required()
@admin_required
def view_logs(current_user):
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
def settings(user):
    return render_template('admin/settings.html')

# 更新系统设置
@admin_bp.route('/settings/update', methods=['POST'])
@admin_required
def update_settings(user):
    # 这里可以添加更新系统设置的逻辑
    flash('系统设置已更新', 'success')
    return redirect(url_for('admin.settings', user=user))

# API: 获取用户列表
@admin_bp.route('/api/users')
@jwt_required()
@admin_required
def api_users(current_user):
    """获取所有用户列表"""
    from user_auth.user_system import User
    
    # 使用SQLAlchemy查询所有用户
    users = User.query.order_by(User.created_at.desc()).all()
    
    # 构建用户列表
    user_list = []
    for user in users:
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'role': 1 if user.is_admin else 0  # 角色信息
        }
        user_list.append(user_dict)
    
    return jsonify(user_list)

# API: 获取系统统计
@admin_bp.route('/api/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_stats(user):
    try:
        # 获取用户总数
        from user_auth.user_system import User
        
        # 使用ORM查询
        #orm_user_count = User.query.count()
        #orm_admin_count = User.query.filter_by(is_admin=True).count()
        
        #logging.info(f"ORM查询结果: 用户总数={orm_user_count}, 管理员数量={orm_admin_count}")
        
        # 使用直接SQL查询作为对照
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        sql_user_count = cursor.fetchone()['COUNT(*)']
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        sql_admin_count = cursor.fetchone()['COUNT(*)']
        
        cursor.close()
        conn.close()
        
        #logging.info(f"SQL查询结果: 用户总数={sql_user_count}, 管理员数量={sql_admin_count}")
        
        # 获取今日登录人数 - 使用登录记录表统计独立用户数
        from datetime import datetime, timedelta
        from user_auth.user_system import LoginRecord
        from sqlalchemy import func
        
        today_start = datetime.combine(datetime.today(), datetime.min.time())
        today_end = today_start + timedelta(days=1)
        
        # 统计今日独立登录用户数
        login_today = db.session.query(
            func.count(func.distinct(LoginRecord.user_id))
        ).filter(
            LoginRecord.login_time >= today_start,
            LoginRecord.login_time < today_end
        ).scalar() or 0
        
        # 获取今日注册用户数
        today_users = User.query.filter(User.created_at >= today_start).count()
        
        # 获取不同会员等级的用户数量
        plus_members = User.query.filter_by(membership_level='plus').count()
        premium_members = User.query.filter_by(membership_level='premium').count()
        
        # 使用SQL结果构建响应
        stats = {
            'user_count': sql_user_count,
            'admin_count': sql_admin_count,
            'active_today': login_today,
            'today_users': today_users,
            'plus_members': plus_members,
            'premium_members': premium_members
        }
        
        #logging.info(f"返回统计数据: {stats}")
        
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取统计数据API错误: {str(e)}")
        return jsonify({"error": f"获取统计数据失败: {str(e)}"}), 500

# 获取用户列表API
@admin_bp.route('/api/users', methods=['GET'])
@jwt_required()
@admin_required
def get_users_api(user):
    try:
        from user_auth.user_system import User
        
        # 获取所有用户
        users_query = User.query.all()
        
        # 转换为JSON格式
        users_list = []
        for user in users_query:
            users_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        return jsonify(users_list)
    except Exception as e:
        logging.error(f"获取用户列表API错误: {str(e)}")
        return jsonify({"error": f"获取用户列表失败: {str(e)}"}), 500

# 用户角色管理API
@admin_bp.route('/api/users/<int:user_id>/role', methods=['PUT'])
@jwt_required()
@admin_required
def update_user_role(user, user_id):
    try:
        from user_auth.user_system import User
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'role' not in data:
            return jsonify({"error": "缺少必要参数"}), 400
            
        role = data['role']
        
        # 查找用户
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({"error": "用户不存在"}), 404
            
        # 不能修改自己的角色
        if target_user.id == user.id:
            return jsonify({"error": "不能修改自己的角色"}), 403
            
        # 更新角色
        is_admin = (role == 'admin')
        
        # 检查是否是最后一个管理员
        if target_user.is_admin and not is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({"error": "不能移除最后一个管理员"}), 400
                
        # 更新用户角色
        target_user.is_admin = is_admin
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"用户 {target_user.username} 角色已更新为 {role}"
        })
    except Exception as e:
        logging.error(f"更新用户角色API错误: {str(e)}")
        return jsonify({"error": f"更新用户角色失败: {str(e)}"}), 500

# 删除用户API
@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user_api(user, user_id):
    try:
        from user_auth.user_system import User, LoginRecord
        
        # 查找用户
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({"error": "用户不存在"}), 404
            
        # 不能删除自己
        if target_user.id == user.id:
            return jsonify({"error": "不能删除自己的账户"}), 403
            
        # 检查是否是最后一个管理员
        if target_user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({"error": "不能删除最后一个管理员"}), 400
                
        # 先删除该用户的所有登录记录
        # 使用原生SQL删除，避免SQLAlchemy关系的干扰
        db.session.execute(
            db.text("DELETE FROM login_records WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        # 删除用户
        db.session.delete(target_user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"用户 {target_user.username} 已成功删除"
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除用户API错误: {str(e)}")
        return jsonify({"error": f"删除用户失败: {str(e)}"}), 500

# 添加管理员登录路由
@admin_bp.route('/login', methods=['GET'])
def admin_login_page():
    """返回管理员登录页面"""
    return send_from_directory('../front_html', 'admin-login.html')

# 获取日志API端点
@admin_bp.route('/api/logs', methods=['GET'])
@jwt_required()
@admin_required
def api_get_logs(current_user):
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
@jwt_required()
@admin_required
def api_get_settings(current_user):
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
@jwt_required()
@admin_required
def api_update_settings(current_user):
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
@jwt_required()
@admin_required
def api_set_admin(current_user, user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({"error": "用户不存在"}), 404
        
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_admin = 1 WHERE id = %s', (user_id,))
        conn.commit()
        conn.close()
        
        logging.info(f"用户 {user['username']} (ID: {user_id}) 已被设置为管理员")
        return jsonify({"message": f"用户 {user['username']} 已设置为管理员", "success": True})
    
    except Exception as e:
        logging.error(f"设置管理员失败: {str(e)}")
        return jsonify({"error": f"设置管理员失败: {str(e)}"}), 500

# 移除管理员权限 API
@admin_bp.route('/api/users/<int:user_id>/remove_admin', methods=['POST'])
@jwt_required()
@admin_required
def api_remove_admin(current_user, user_id):
    try:
        # 获取当前用户信息
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        current_user_data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE public_id = %s', 
                    (current_user_data['public_id'],))
        current_user = cursor.fetchone()
        
        # 检查是否是自己
        if current_user and current_user['id'] == user_id:
            conn.close()
            logging.warning(f"用户 {current_user['username']} (ID: {user_id}) 尝试移除自己的管理员权限")
            return jsonify({"error": "不能移除自己的管理员权限"}), 400
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            logging.error(f"尝试移除管理员权限失败：用户不存在，ID: {user_id}")
            return jsonify({"error": "用户不存在"}), 404
        
        # 检查是否是最后一个管理员
        if user['is_admin']:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
            admin_count = cursor.fetchone()['COUNT(*)']
            if admin_count <= 1:
                conn.close()
                logging.error(f"尝试移除管理员权限失败：不能移除最后一个管理员 ({user['username']}, ID: {user_id})")
                return jsonify({"error": "不能移除最后一个管理员"}), 400
        
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_admin = 0 WHERE id = %s', (user_id,))
        conn.commit()
        conn.close()
        
        logging.info(f"已移除用户 {user['username']} (ID: {user_id}) 的管理员权限")
        return jsonify({"message": f"已移除 {user['username']} 的管理员权限", "success": True})
    
    except Exception as e:
        logging.error(f"移除管理员权限失败: {str(e)}")
        return jsonify({"error": f"移除管理员权限失败: {str(e)}"}), 500

# 管理员登录API
@admin_bp.route('/api/login', methods=['POST'])
def admin_login_api():
    """管理员登录API"""
    from user_auth.user_system import User
    from flask_jwt_extended import create_access_token
    from werkzeug.security import check_password_hash
    
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        # 验证输入
        if not username or not password:
            return jsonify({'message': '用户名和密码不能为空', 'success': False}), 400
        
        # 查询用户
        user = User.query.filter_by(username=username).first()
        
        # 验证用户和密码
        if not user or not check_password_hash(user.password, password):
            return jsonify({'message': '用户名或密码错误', 'success': False}), 401
        
        # 验证是否是管理员
        if not user.is_admin:
            return jsonify({'message': '您没有管理员权限', 'success': False}), 403
        
        # 更新最后登录时间
        user.last_login = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        db.session.commit()
        
        # 创建令牌
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        })
        
    except Exception as e:
        return jsonify({'message': f'登录失败: {str(e)}', 'success': False}), 500