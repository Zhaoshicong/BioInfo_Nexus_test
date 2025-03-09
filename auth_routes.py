from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import uuid
from user_system import db, User, TokenBlacklist, token_required
import os
from werkzeug.utils import secure_filename
import secrets
from flask_mail import Mail, Message
from flask import render_template
import logging

# 创建logger
logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

# 初始化邮件服务
mail = Mail()

# 注册路由
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['email', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'缺少必填字段: {field}'}), 400
    
    email = data['email']
    # 从邮箱中提取用户名（使用@前的部分）
    username = email.split('@')[0]
    
    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({'message': '用户名已存在！'}), 409
    
    # 检查邮箱是否已存在
    if User.query.filter_by(email=email).first():
        return jsonify({'message': '邮箱已被注册！'}), 409
    
    # 创建新用户
    hashed_password = generate_password_hash(data['password'])
    verification_token = secrets.token_hex(16)
    
    new_user = User(
        public_id=str(uuid.uuid4()),
        username=username,
        email=email,
        password=hashed_password,
        is_active=False,
        verification_token=verification_token
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    # 发送验证邮件
    send_verification_email(email, verification_token)
    
    return jsonify({'message': '注册成功！请查收验证邮件以激活您的账户。'}), 201

# 邮箱验证路由
@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        # 验证失败，重定向到首页并显示错误消息
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>验证失败</title>
            <meta http-equiv="refresh" content="5;url=/" />
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }}
                .message {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; }}
                .countdown {{ font-weight: bold; }}
            </style>
            <script>
                let seconds = 5;
                function updateCountdown() {{
                    document.getElementById('countdown').textContent = seconds;
                    if (seconds <= 0) {{
                        window.location.href = '/';
                    }} else {{
                        seconds--;
                        setTimeout(updateCountdown, 1000);
                    }}
                }}
                window.onload = updateCountdown;
            </script>
        </head>
        <body>
            <div class="message">
                <h2>验证失败</h2>
                <p>无效的验证链接！</p>
                <p><span class="countdown" id="countdown">5</span> 秒后将自动跳转到首页...</p>
                <p>如果没有自动跳转，请<a href="/">点击这里</a>。</p>
            </div>
        </body>
        </html>
        """
    
    user.is_active = True
    user.verification_token = None
    db.session.commit()
    
    # 验证成功，重定向到首页并显示成功消息
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>验证成功</title>
        <meta http-equiv="refresh" content="5;url=/" />
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }}
            .message {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; }}
            .countdown {{ font-weight: bold; }}
        </style>
        <script>
            let seconds = 5;
            function updateCountdown() {{
                document.getElementById('countdown').textContent = seconds;
                if (seconds <= 0) {{
                    window.location.href = '/';
                }} else {{
                    seconds--;
                    setTimeout(updateCountdown, 1000);
                }}
            }}
            window.onload = updateCountdown;
        </script>
    </head>
    <body>
        <div class="message">
            <h2>验证成功</h2>
            <p>邮箱验证成功！您现在可以登录了。</p>
            <p><span class="countdown" id="countdown">5</span> 秒后将自动跳转到首页...</p>
            <p>如果没有自动跳转，请<a href="/">点击这里</a>。</p>
        </div>
    </body>
    </html>
    """

# 重新发送验证邮件
@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'message': '请提供邮箱地址！'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'message': '该邮箱未注册！'}), 404
    
    if user.is_active:
        return jsonify({'message': '该账户已激活，无需重新验证！'}), 400
    
    # 生成新的验证令牌
    verification_token = secrets.token_hex(16)
    user.verification_token = verification_token
    db.session.commit()
    
    # 发送验证邮件
    send_verification_email(user.email, verification_token)
    
    return jsonify({'message': '验证邮件已重新发送，请查收！'}), 200

# 登录路由
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': '请提供邮箱和密码！'}), 400
    
    # 查找用户（支持使用邮箱登录）
    user = User.query.filter_by(email=data['username']).first()
    
    # 如果没找到，尝试使用用户名查找（向后兼容）
    if not user:
        user = User.query.filter_by(username=data['username']).first()
    
    if not user:
        return jsonify({'message': '邮箱或密码错误！'}), 401
    
    # 检查账户是否已激活
    if not user.is_active:
        return jsonify({
            'message': '账户未激活！请先验证您的邮箱。',
            'email': user.email,
            'needs_verification': True
        }), 401
    
    # 验证密码
    if check_password_hash(user.password, data['password']):
        # 生成JWT令牌
        token_payload = {
            'public_id': user.public_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }
        
        token = jwt.encode(
            token_payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return jsonify({
            'token': token,
            'public_id': user.public_id,
            'username': user.username,
            'message': '登录成功！'
        }), 200
    
    return jsonify({'message': '邮箱或密码错误！'}), 401

# 发送验证邮件的函数
def send_verification_email(user_email, token):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # 获取邮件配置
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']
        smtp_username = current_app.config['MAIL_USERNAME']
        smtp_password = current_app.config['MAIL_PASSWORD']
        use_tls = current_app.config['MAIL_USE_TLS']
        use_ssl = current_app.config['MAIL_USE_SSL']
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = "BioInfoNexus <bioinfo-nexus@o41w.ren>"
        msg['To'] = user_email
        msg['Subject'] = "BioInfoNexus - Email Verification"
        
        # 设置邮件内容
        verification_url = f"{request.host_url.rstrip('/')}/api/auth/verify-email/{token}"
        body = f"""
Thank you for registering with BioInfoNexus!

Please click the following link to verify your email:
{verification_url}

If you did not register for a BioInfoNexus account, please ignore this email.

BioInfoNexus Team
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 连接到SMTP服务器并发送邮件
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls()
        
        # 登录
        server.login(smtp_username, smtp_password)
        
        # 发送邮件
        server.send_message(msg)
        
        # 关闭连接
        server.quit()
        
        print(f"邮件已成功发送到 {user_email}")
        return True
    except Exception as e:
        import traceback
        error_msg = f"发送邮件错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # 打印到控制台
        try:
            logger.error(error_msg)
        except:
            pass
        return False

# 注销路由
@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        
        # 将令牌加入黑名单
        blacklist_token = TokenBlacklist(token=token)
        db.session.add(blacklist_token)
        db.session.commit()
        
        return jsonify({'message': '注销成功！'}), 200
    
    return jsonify({'message': '无效的令牌！'}), 400

# 获取当前用户信息
@auth_bp.route('/me', methods=['GET'])
@token_required
def get_user_info(current_user):
    user_data = {
        'id': current_user.public_id,
        'username': current_user.username,
        'email': current_user.email,
        'is_admin': current_user.is_admin,
        'created_at': current_user.created_at,
        'last_login': current_user.last_login
    }
    
    return jsonify(user_data), 200

# 更新用户信息
@auth_bp.route('/me', methods=['PUT'])
@token_required
def update_user_info(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({'message': '没有提供数据！'}), 400
    
    # 更新可编辑字段
    if data.get('email') and data['email'] != current_user.email:
        # 检查邮箱是否已被其他用户使用
        if User.query.filter(User.email == data['email'], User.id != current_user.id).first():
            return jsonify({'message': '邮箱已被其他用户注册！'}), 409
        current_user.email = data['email']
    
    # 更新密码
    if data.get('password'):
        current_user.password = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({'message': '用户信息更新成功！'}), 200

# 辅助函数：检查文件类型是否允许
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 