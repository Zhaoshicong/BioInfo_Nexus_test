from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
import sqlite3
import os
from datetime import datetime

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 数据库连接函数
def get_db_connection():
    conn = sqlite3.connect('instance/database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 管理员权限检查装饰器
def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user_id = get_jwt_identity()
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE id = ?', (current_user_id,)).fetchone()
        conn.close()
        
        if not user or user['role'] != 'admin':
            return jsonify({"message": "管理员权限需要"}), 403
        return f(*args, **kwargs)
    return decorated

# 管理面板首页
@admin_bp.route('/')
@admin_required
def admin_panel():
    conn = get_db_connection()
    
    # 获取用户统计
    user_count = conn.execute('SELECT COUNT(*) FROM user').fetchone()[0]
    admin_count = conn.execute('SELECT COUNT(*) FROM user WHERE role = "admin"').fetchone()[0]
    
    # 获取最近注册的用户
    recent_users = conn.execute('SELECT id, username, email, registered_on FROM user ORDER BY registered_on DESC LIMIT 5').fetchall()
    
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
def manage_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM user ORDER BY registered_on DESC').fetchall()
    conn.close()
    return render_template('admin/users.html', users=[dict(u) for u in users])

# 查看单个用户
@admin_bp.route('/users/<int:user_id>')
@admin_required
def view_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/user_detail.html', user=dict(user))

# 设置用户为管理员
@admin_bp.route('/users/<int:user_id>/set_admin', methods=['POST'])
@admin_required
def set_admin(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    conn.execute('UPDATE user SET role = "admin" WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'用户 {user["username"]} 已设置为管理员', 'success')
    return redirect(url_for('admin.manage_users'))

# 移除管理员权限
@admin_bp.route('/users/<int:user_id>/remove_admin', methods=['POST'])
@admin_required
def remove_admin(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    conn.execute('UPDATE user SET role = "user" WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'已移除 {user["username"]} 的管理员权限', 'success')
    return redirect(url_for('admin.manage_users'))

# 删除用户
@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('用户不存在', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # 检查是否是最后一个管理员
    if user['role'] == 'admin':
        admin_count = conn.execute('SELECT COUNT(*) FROM user WHERE role = "admin"').fetchone()[0]
        if admin_count <= 1:
            conn.close()
            flash('不能删除最后一个管理员', 'error')
            return redirect(url_for('admin.manage_users'))
    
    conn.execute('DELETE FROM user WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'用户 {user["username"]} 已删除', 'success')
    return redirect(url_for('admin.manage_users'))

# 系统日志
@admin_bp.route('/logs')
@admin_required
def view_logs():
    log_file = 'logs/app.log'
    logs = []
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = f.readlines()[-100:]  # 获取最后100行
    
    return render_template('admin/logs.html', logs=logs)

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
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, email, role, registered_on FROM user').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

# API: 获取系统统计
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    conn = get_db_connection()
    
    # 用户统计
    user_count = conn.execute('SELECT COUNT(*) FROM user').fetchone()[0]
    admin_count = conn.execute('SELECT COUNT(*) FROM user WHERE role = "admin"').fetchone()[0]
    
    # 其他统计数据可以根据需要添加
    
    conn.close()
    
    return jsonify({
        'user_count': user_count,
        'admin_count': admin_count,
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }) 