from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import uuid
from .user_system import db, User, TokenBlacklist, token_required
import os
from werkzeug.utils import secure_filename
import secrets
from flask_mail import Mail, Message
from flask import render_template
import logging
import random
import string
import time

# 创建logger
logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

# 初始化邮件服务
mail = Mail()

# 生成随机验证码
def generate_verification_code(length=6):
    return ''.join(random.choice(string.digits) for _ in range(length))

# 注册路由
@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # 记录注册请求
        print(f"收到注册请求: {data}")
        
        # 验证必填字段
        required_fields = ['email', 'password', 'verification_code']
        for field in required_fields:
            if not data.get(field):
                print(f"缺少必填字段: {field}")
                return jsonify({'message': f'缺少必填字段: {field}'}), 400
        
        email = data['email']
        verification_code = data['verification_code']
        # 从邮箱中提取用户名（使用@前的部分）
        username = email.split('@')[0]
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.is_active:
            print(f"用户名已存在: {username}")
            return jsonify({'message': '用户名已存在！'}), 409
        
        # 检查邮箱是否已存在且已激活
        existing_email = User.query.filter_by(email=email, is_active=True).first()
        if existing_email:
            print(f"邮箱已被注册: {email}")
            return jsonify({'message': '邮箱已被注册！'}), 409
        
        # 验证验证码
        user_record = User.query.filter_by(email=email, verification_code=verification_code, is_active=False).first()
        
        print(f"查找用户记录: email={email}, verification_code={verification_code}, 结果: {user_record}")
        
        if not user_record:
            # 检查是否存在临时记录
            temp_user = User.query.filter_by(email=email, is_active=False).first()
            if temp_user:
                print(f"验证码错误: 用户临时记录存在 {temp_user.email}, 但验证码不匹配或为空")
                # 验证码错误
                return jsonify({'message': '验证码错误或已过期！'}), 400
            
            print(f"没有找到用户临时记录: {email}")
            # 创建新的临时用户记录
            return jsonify({'message': '请先获取验证码！'}), 400
        
        # 验证验证码是否过期
        if user_record.verification_code_expiry and user_record.verification_code_expiry < datetime.datetime.utcnow():
            print(f"验证码已过期: {email}, 过期时间: {user_record.verification_code_expiry}")
            return jsonify({'message': '验证码已过期，请重新获取！'}), 400
        
        # 更新用户信息并激活账户
        user_record.password = generate_password_hash(data['password'])
        user_record.is_active = True
        user_record.verification_code = None
        user_record.verification_code_expiry = None
        
        try:
            db.session.commit()
            print(f"用户注册成功: {email}")
            return jsonify({'message': '注册成功！您现在可以登录了。'}), 201
        except Exception as e:
            db.session.rollback()
            print(f"数据库提交错误: {str(e)}")
            return jsonify({'message': f'数据库错误: {str(e)}'}), 500
    
    except Exception as e:
        print(f"注册过程中发生异常: {str(e)}")
        return jsonify({'message': f'注册失败: {str(e)}'}), 500

# 发送注册验证码
@auth_bp.route('/send-register-code', methods=['POST'])
def send_register_code():
    try:
        print("开始处理发送注册验证码请求")
        
        # 检查请求内容类型和数据格式
        content_type = request.headers.get('Content-Type', '')
        print(f"请求Content-Type: {content_type}")
        
        if 'application/json' in content_type:
            try:
                data = request.get_json()
                print(f"JSON数据: {data}")
            except Exception as e:
                print(f"解析JSON数据失败: {str(e)}")
                return jsonify({'message': '无效的JSON格式'}), 400
        else:
            try:
                # 尝试从表单数据中获取
                data = request.form.to_dict()
                print(f"表单数据: {data}")
                if not data:
                    # 尝试从请求体中获取原始数据
                    data_str = request.data.decode('utf-8')
                    print(f"原始请求数据: {data_str}")
                    # 尝试解析为JSON
                    try:
                        import json
                        data = json.loads(data_str)
                        print(f"从原始数据解析的JSON: {data}")
                    except:
                        print("无法解析原始数据为JSON")
            except Exception as e:
                print(f"处理非JSON数据失败: {str(e)}")
                return jsonify({'message': '无法解析请求数据'}), 400
        
        if not data:
            print("请求中没有数据")
            return jsonify({'message': '请求中没有数据'}), 400
        
        if not data.get('email'):
            print("请求中没有提供邮箱地址")
            return jsonify({'message': '请提供邮箱地址！'}), 400
        
        email = data['email']
        print(f"请求中提供的邮箱: {email}")
        
        # 验证邮箱格式
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            print(f"邮箱格式无效: {email}")
            return jsonify({'message': '邮箱格式无效！'}), 400
        
        # 检查邮箱是否已注册且已激活
        active_user = User.query.filter_by(email=email, is_active=True).first()
        if active_user:
            print(f"邮箱已被注册且已激活: {email}")
            return jsonify({'message': '该邮箱已被注册！'}), 409
        
        # 生成验证码
        verification_code = generate_verification_code()
        print(f"为 {email} 生成验证码: {verification_code}")
        
        # 设置验证码过期时间（10分钟）
        expiry_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
        
        # 检查是否已存在未激活的用户记录
        temp_user = User.query.filter_by(email=email, is_active=False).first()
        
        if temp_user:
            print(f"更新现有临时用户记录: {email}")
            # 更新现有记录
            temp_user.verification_code = verification_code
            temp_user.verification_code_expiry = expiry_time
        else:
            print(f"创建新的临时用户记录: {email}")
            # 创建新的临时用户记录
            username = email.split('@')[0]
            public_id = str(uuid.uuid4())
            
            new_user = User(
                public_id=public_id,
                username=username,
                email=email,
                password='temporary_password',  # 将在注册完成时更新
                is_active=False,
                verification_code=verification_code,
                verification_code_expiry=expiry_time
            )
            db.session.add(new_user)
        
        try:
            db.session.commit()
            print(f"数据库更新成功: {email}")
        except Exception as e:
            db.session.rollback()
            print(f"数据库更新失败: {str(e)}")
            return jsonify({'message': f'服务器错误: {str(e)}'}), 500
        
        # 发送验证码邮件
        print(f"准备向 {email} 发送验证码")
        result = send_verification_code_email(email, verification_code)
        
        if result:
            print(f"验证码邮件发送成功: {email}")
            return jsonify({'message': '验证码已发送，请查收邮件！'}), 200
        else:
            print(f"验证码邮件发送失败: {email}")
            return jsonify({'message': '发送验证码失败，请稍后再试！'}), 500
    
    except Exception as e:
        import traceback
        print(f"发送验证码过程中发生异常: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'message': f'发送验证码失败: {str(e)}'}), 500

# 发送验证码邮件的函数
def send_verification_code_email(user_email, code):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import traceback
        
        print(f"开始发送验证码邮件到 {user_email}")
        
        # 获取邮件配置
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']
        smtp_username = current_app.config['MAIL_USERNAME']
        smtp_password = current_app.config['MAIL_PASSWORD']
        use_tls = current_app.config['MAIL_USE_TLS']
        use_ssl = current_app.config['MAIL_USE_SSL']
        
        print(f"邮件配置: 服务器={smtp_server}, 端口={smtp_port}, 用户名={smtp_username}, TLS={use_tls}, SSL={use_ssl}")
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = "BioInfoNexus <bioinfo-nexus@o41w.ren>"
        msg['To'] = user_email
        msg['Subject'] = "BioInfoNexus - 验证码"
        
        # 设置邮件内容
        body = f"""
尊敬的用户，

您好！感谢您注册BioInfoNexus。

您的验证码是: {code}

此验证码将在10分钟内有效。如果您没有进行任何操作，请忽略此邮件。

BioInfoNexus 团队
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        print(f"准备连接到SMTP服务器 {smtp_server}:{smtp_port}")
        
        # 最大重试次数
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                retry_count += 1
                print(f"尝试发送邮件 (第{retry_count}次尝试)")
                
                # 连接到SMTP服务器并发送邮件
                if use_ssl:
                    print("使用SSL连接")
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
                else:
                    print("使用普通连接")
                    server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                    if use_tls:
                        print("启用TLS")
                        server.starttls()
                
                server.set_debuglevel(1)  # 启用SMTP调试
                
                # 登录
                print(f"尝试登录邮件服务器，用户名: {smtp_username}")
                server.login(smtp_username, smtp_password)
                
                # 发送邮件
                print(f"登录成功，发送邮件到 {user_email}")
                server.send_message(msg)
                
                # 关闭连接
                server.quit()
                
                print(f"验证码邮件已成功发送到 {user_email}")
                return True
                
            except smtplib.SMTPAuthenticationError as auth_error:
                print(f"SMTP认证错误 (尝试 {retry_count}/{max_retries}): {str(auth_error)}")
                last_error = auth_error
                # 认证错误通常无法通过重试解决，直接返回
                break
                
            except (smtplib.SMTPException, ConnectionError, TimeoutError) as e:
                print(f"SMTP错误 (尝试 {retry_count}/{max_retries}): {str(e)}")
                last_error = e
                if retry_count < max_retries:
                    # 等待一段时间后重试
                    wait_time = 2 ** retry_count  # 指数退避
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    
        # 如果所有尝试都失败，尝试用Flask-Mail发送
        try:
            print("所有SMTP尝试失败，尝试使用Flask-Mail发送")
            from flask_mail import Message
            msg = Message(
                subject="BioInfoNexus - 验证码",
                recipients=[user_email],
                body=body,
                sender=("BioInfoNexus", "bioinfo-nexus@o41w.ren")
            )
            mail.send(msg)
            print(f"使用Flask-Mail成功发送验证码到 {user_email}")
            return True
        except Exception as mail_error:
            print(f"Flask-Mail发送失败: {str(mail_error)}")
            print(f"所有发送尝试均失败，最后错误: {last_error or mail_error}")
            print(f"错误详情: {traceback.format_exc()}")
            return False
        
    except Exception as e:
        print(f"发送验证码邮件时发生未预期的异常: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return False

# 忘记密码路由（发送验证码）
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    
    print(f"收到忘记密码请求: {data}")
    
    if not data or not data.get('email'):
        print("请求中没有提供邮箱地址")
        return jsonify({'message': '请提供邮箱地址！'}), 400
    
    user_email = data['email']
    print(f"正在查找用户: {user_email}")
    
    user = User.query.filter_by(email=user_email).first()
    
    if not user:
        print(f"用户不存在: {user_email}")
        # 为了安全，即使用户不存在也返回成功消息
        return jsonify({'message': '验证码已发送，请查收邮件。'}), 200
    
    print(f"找到用户: {user.username}, ID: {user.id}")
    
    # 生成重置验证码
    reset_code = generate_verification_code()
    print(f"生成重置验证码: {reset_code}")
    
    # 设置验证码过期时间（10分钟）
    user.reset_code = reset_code
    user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    
    try:
        db.session.commit()
        print("数据库更新成功")
    except Exception as e:
        print(f"数据库更新失败: {str(e)}")
        db.session.rollback()
        return jsonify({'message': '服务器错误，请稍后再试。'}), 500
    
    # 发送重置密码邮件
    print(f"准备发送重置密码验证码到: {user.email}")
    result = send_reset_password_code_email(user.email, reset_code)
    
    if result:
        print(f"重置密码验证码邮件发送成功: {user.email}")
        return jsonify({'message': '验证码已发送到您的邮箱，请查收。'}), 200
    else:
        print(f"重置密码验证码邮件发送失败: {user.email}")
        return jsonify({'message': '发送验证码失败，请稍后再试。'}), 500

# 使用验证码重置密码
@auth_bp.route('/reset-password-with-code', methods=['POST'])
def reset_password_with_code():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('verification_code') or not data.get('password'):
        return jsonify({'message': '请提供所有必要信息！'}), 400
    
    email = data['email']
    verification_code = data['verification_code']
    new_password = data['password']
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'message': '该邮箱未注册！'}), 404
    
    # 验证验证码
    if not user.reset_code or user.reset_code != verification_code:
        return jsonify({'message': '验证码错误！'}), 400
    
    # 检查验证码是否过期
    if user.reset_token_expiry and user.reset_token_expiry < datetime.datetime.utcnow():
        return jsonify({'message': '验证码已过期，请重新获取！'}), 400
    
    # 更新密码
    user.password = generate_password_hash(new_password)
    user.reset_code = None
    user.reset_token_expiry = None
    db.session.commit()
    
    return jsonify({'message': '密码重置成功！您现在可以使用新密码登录。'}), 200

# 发送重置密码验证码邮件的函数
def send_reset_password_code_email(user_email, code):
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
        msg['Subject'] = "BioInfoNexus - 密码重置验证码"
        
        # 设置邮件内容
        body = f"""
尊敬的用户，

您好！您申请了重置BioInfoNexus账户密码。

您的重置密码验证码是: {code}

此验证码将在10分钟内有效。如果您没有申请重置密码，请忽略此邮件。

BioInfoNexus 团队
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
        
        print(f"重置密码验证码邮件已成功发送到 {user_email}")
        return True
    except Exception as e:
        print(f"发送重置密码验证码邮件失败: {str(e)}")
        return False

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
    
    if not data:
        return jsonify({'message': '无效的请求数据！'}), 400
        
    # 支持使用email或username登录
    if data.get('email'):
        username_or_email = data.get('email')
    elif data.get('username'):
        username_or_email = data.get('username')
    else:
        return jsonify({'message': '请提供邮箱或用户名！'}), 400
        
    if not data.get('password'):
        return jsonify({'message': '请提供密码！'}), 400
    
    # 查找用户（支持使用邮箱登录）
    user = User.query.filter_by(email=username_or_email).first()
    
    # 如果没找到，尝试使用用户名查找
    if not user:
        user = User.query.filter_by(username=username_or_email).first()
    
    if not user:
        return jsonify({'message': '邮箱/用户名或密码错误！'}), 401
    
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
        
        # 获取用户角色
        role = 'admin' if user.is_admin else 'user'
        
        return jsonify({
            'token': token,
            'user_id': user.id,
            'public_id': user.public_id,
            'username': user.username,
            'email': user.email,
            'role': role,
            'message': '登录成功！'
        }), 200
    
    return jsonify({'message': '邮箱/用户名或密码错误！'}), 401

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

# 验证重置令牌路由
@auth_bp.route('/verify-reset-token/<token>', methods=['GET'])
def verify_reset_token(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or user.reset_token_expiry < datetime.datetime.utcnow():
        return jsonify({'valid': False, 'message': '无效或已过期的重置链接！'}), 400
    
    return jsonify({'valid': True, 'message': '有效的重置链接。'}), 200

# 发送重置密码邮件的函数
def send_reset_password_email(user_email, token):
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
        msg['Subject'] = "BioInfoNexus - Password Reset"
        
        # 设置邮件内容
        reset_url = f"{request.host_url.rstrip('/')}/reset-password.html?token={token}"
        body = f"""
Hello,

You have requested to reset your password for your BioInfoNexus account.

Please click the following link to reset your password:
{reset_url}

This link will expire in 24 hours.

If you did not request a password reset, please ignore this email.

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
        
        print(f"重置密码邮件已成功发送到 {user_email}")
        return True
    except Exception as e:
        import traceback
        error_msg = f"发送重置密码邮件错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # 打印到控制台
        try:
            logger.error(error_msg)
        except:
            pass
        return False 

# 测试邮件服务器连接
@auth_bp.route('/test-mail-connection', methods=['GET'])
def test_mail_connection():
    try:
        import smtplib
        import traceback
        
        print("开始测试邮件服务器连接")
        
        # 获取邮件配置
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']
        smtp_username = current_app.config['MAIL_USERNAME']
        smtp_password = current_app.config['MAIL_PASSWORD']
        use_tls = current_app.config['MAIL_USE_TLS']
        use_ssl = current_app.config['MAIL_USE_SSL']
        
        print(f"邮件配置: 服务器={smtp_server}, 端口={smtp_port}, 用户名={smtp_username}, TLS={use_tls}, SSL={use_ssl}")
        
        result = {
            'config': {
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_username': smtp_username,
                'use_tls': use_tls,
                'use_ssl': use_ssl
            },
            'tests': []
        }
        
        # 测试1: 检查DNS解析
        try:
            import socket
            print(f"尝试解析邮件服务器域名: {smtp_server}")
            ip = socket.gethostbyname(smtp_server)
            print(f"DNS解析成功: {smtp_server} -> {ip}")
            result['tests'].append({
                'name': 'DNS解析',
                'success': True,
                'message': f'成功解析为 {ip}'
            })
        except Exception as e:
            print(f"DNS解析失败: {str(e)}")
            result['tests'].append({
                'name': 'DNS解析',
                'success': False,
                'message': str(e)
            })
        
        # 测试2: 尝试连接到SMTP服务器
        try:
            print(f"尝试连接到SMTP服务器: {smtp_server}:{smtp_port}")
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            
            print("SMTP服务器连接成功")
            result['tests'].append({
                'name': 'SMTP连接',
                'success': True,
                'message': '连接成功'
            })
            
            # 测试3: 尝试TLS连接(如果启用)
            if use_tls and not use_ssl:
                try:
                    print("尝试启用TLS")
                    server.starttls()
                    print("TLS连接成功")
                    result['tests'].append({
                        'name': 'TLS连接',
                        'success': True,
                        'message': 'TLS连接成功'
                    })
                except Exception as e:
                    print(f"TLS连接失败: {str(e)}")
                    result['tests'].append({
                        'name': 'TLS连接',
                        'success': False,
                        'message': str(e)
                    })
            
            # 测试4: 尝试登录
            try:
                print(f"尝试登录SMTP服务器，用户名: {smtp_username}")
                server.login(smtp_username, smtp_password)
                print("SMTP登录成功")
                result['tests'].append({
                    'name': 'SMTP认证',
                    'success': True,
                    'message': '认证成功'
                })
            except Exception as e:
                print(f"SMTP登录失败: {str(e)}")
                result['tests'].append({
                    'name': 'SMTP认证',
                    'success': False,
                    'message': str(e)
                })
            
            # 关闭连接
            try:
                server.quit()
            except:
                pass
            
        except Exception as e:
            print(f"SMTP连接失败: {str(e)}")
            result['tests'].append({
                'name': 'SMTP连接',
                'success': False,
                'message': str(e)
            })
        
        # 汇总测试结果
        all_success = all(test['success'] for test in result['tests'])
        result['overall_success'] = all_success
        result['message'] = '所有测试通过' if all_success else '部分测试失败'
        
        return jsonify(result)
    
    except Exception as e:
        print(f"测试邮件服务器连接时发生异常: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'测试过程中发生异常: {str(e)}'
        }), 500 

# 发送测试邮件
@auth_bp.route('/send-test-email', methods=['POST'])
def send_test_email():
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({'message': '请提供邮箱地址！'}), 400
        
        email = data['email']
        
        # 发送测试邮件
        result = send_verification_code_email(email, "TEST123")
        
        if result:
            return jsonify({'message': '测试邮件已发送！'}), 200
        else:
            return jsonify({'message': '测试邮件发送失败！'}), 500
    
    except Exception as e:
        import traceback
        print(f"发送测试邮件时发生异常: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'message': f'发送测试邮件失败: {str(e)}'}), 500 