from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import datetime
import jwt
import os
from functools import wraps

# 数据库配置
db = SQLAlchemy()

# 用户模型
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=False)  # 默认为False，需要邮箱验证
    is_admin = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)  # 密码重置令牌
    reset_token_expiry = db.Column(db.DateTime, nullable=True)  # 令牌过期时间
    
    def __repr__(self):
        return f'<User {self.username}>'

# 令牌黑名单模型（用于注销）
class TokenBlacklist(db.Model):
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<TokenBlacklist {self.id}>'

# 初始化用户系统
def init_user_system(app):
    # 配置数据库
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bioinfo_nexus.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建所有表
    with app.app_context():
        db.create_all()
        
        # 创建管理员账户（如果不存在）
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                public_id=str(uuid.uuid4()),
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

# JWT令牌验证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 从请求头中获取令牌
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': '缺少令牌！'}), 401
        
        # 检查令牌是否在黑名单中
        blacklisted_token = TokenBlacklist.query.filter_by(token=token).first()
        if blacklisted_token:
            return jsonify({'message': '令牌已失效！'}), 401
        
        try:
            # 解码令牌
            from flask import current_app
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(public_id=data['public_id']).first()
            
            if not current_user:
                return jsonify({'message': '无效的令牌！'}), 401
                
            if not current_user.is_active:
                return jsonify({'message': '账户已被禁用！'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '令牌已过期！'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '无效的令牌！'}), 401
        except Exception as e:
            return jsonify({'message': f'令牌验证出错: {str(e)}'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

# 管理员权限验证装饰器
def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'message': '需要管理员权限！'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated 