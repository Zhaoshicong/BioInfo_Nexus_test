from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import datetime
import jwt
import os
import enum
from functools import wraps
from dotenv import load_dotenv

# 数据库配置
db = SQLAlchemy()

# 定义会员等级枚举类
class MembershipLevel(enum.Enum):
    FREE = "free"      # 默认免费用户
    PLUS = "plus"      # Plus会员
    PREMIUM = "premium"  # Premium会员
    
    def __str__(self):
        return self.value

# 用户模型
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=8))
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=False)  # 默认为False，需要邮箱验证
    is_admin = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    verification_code = db.Column(db.String(10), nullable=True)  # 验证码
    verification_code_expiry = db.Column(db.DateTime, nullable=True)  # 验证码过期时间
    reset_token = db.Column(db.String(100), unique=True, nullable=True)  # 密码重置令牌
    reset_token_expiry = db.Column(db.DateTime, nullable=True)  # 令牌过期时间
    reset_code = db.Column(db.String(10), nullable=True)  # 重置密码验证码
    
    # 会员相关字段
    membership_level = db.Column(db.String(20), default=MembershipLevel.FREE.value)
    membership_expiry = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
        
    def to_dict(self):
        """将用户对象转换为字典格式"""
        return {
            'id': self.id,
            'public_id': self.public_id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'membership_level': self.membership_level,
            'membership_expiry': self.membership_expiry.isoformat() if self.membership_expiry else None,
            'is_membership_active': self.is_membership_active()
        }
        
    def is_membership_active(self):
        """检查用户会员是否在有效期内"""
        if self.is_admin:  # 管理员默认拥有所有权限
            return True
        if self.membership_level == MembershipLevel.FREE.value:
            return True  # 免费用户始终"有效"
        if self.membership_expiry and self.membership_expiry > datetime.datetime.utcnow() + datetime.timedelta(hours=8):
            return True
        return False
    
    def has_membership_level(self, required_level):
        """检查用户是否拥有指定或更高的会员等级"""
        if not self.is_membership_active():
            return False
            
        # 会员等级层次关系
        level_hierarchy = {
            MembershipLevel.FREE.value: 0,
            MembershipLevel.PLUS.value: 1,
            MembershipLevel.PREMIUM.value: 2
        }
        
        user_level = level_hierarchy.get(self.membership_level, 0)
        required_level_value = level_hierarchy.get(required_level, 0) 
        
        return user_level >= required_level_value

# 令牌黑名单模型（用于注销）
class TokenBlacklist(db.Model):
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=8))
    
    def __repr__(self):
        return f'<TokenBlacklist {self.id}>'

# 登录记录模型（用于统计每日登录人数）
class LoginRecord(db.Model):
    __tablename__ = 'login_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=8), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # 支持IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('login_records', lazy=True))
    
    def __repr__(self):
        return f'<LoginRecord {self.user_id} at {self.login_time}>'
    
    def to_dict(self):
        """将登录记录对象转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

# AI使用记录模型（用于追踪AI分析使用次数）
class AIUsageRecord(db.Model):
    __tablename__ = 'ai_usage_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    usage_date = db.Column(db.DateTime, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=8), nullable=False)
    tool_name = db.Column(db.String(100), nullable=True)  # 使用的工具名称（可选）
    sequence_length = db.Column(db.Integer, nullable=True)  # 序列长度（可选）
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('ai_usage_records', lazy=True))
    
    def __repr__(self):
        return f'<AIUsageRecord {self.user_id} at {self.usage_date}>'
    
    def to_dict(self):
        """将AI使用记录对象转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'usage_date': self.usage_date.isoformat() if self.usage_date else None,
            'tool_name': self.tool_name,
            'sequence_length': self.sequence_length
        }

# 初始化用户系统
def init_user_system(app):
    # 加载环境变量
    load_dotenv()
    
    # 配置MySQL数据库
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_db = os.environ.get('MYSQL_DB')
    
    print(f"MySQL 配置: 用户={mysql_user}, 主机={mysql_host}, 数据库={mysql_db}, 端口={mysql_port}")
    
    if not all([mysql_user, mysql_password, mysql_host, mysql_db]):
        raise ValueError("MySQL 配置不完整，请检查 .env 文件中的 MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB")
        
    # 使用 pymysql 驱动
    db_uri = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    print(f"已配置使用 MySQL 数据库: {mysql_host}/{mysql_db}")
    print(f"数据库 URI: {db_uri}")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 30,  # 连接池的大小
        'max_overflow': 40,  # 超过pool_size后，最多可以创建的额外连接数
        'pool_timeout': 30,  # 等待池中连接的超时时间（秒）
        'pool_recycle': 1800,  # 连接在池中的最大生存时间（秒）
        'pool_pre_ping': True,  # 在使用连接前检查连接有效性，自动重连断开的连接
    }
    # SECRET_KEY 已在 app.py 中加载，这里不再重复设置
    # app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')
    
    # 初始化数据库
    db.init_app(app)
    
    print(f"最终使用的数据库 URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("="*50 + "\n")
    
    # 创建所有表 (如果它们不存在)
    with app.app_context():
        print("正在创建数据库表（如果不存在）...")
        # 直接创建所有表，不尝试反射
        db.create_all()
        print("数据库表已创建完成。")
        
        # 尝试创建初始管理员用户
        try:
            # 检查是否有管理员账户
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count == 0:
                print("没有找到管理员账户，正在创建默认管理员...")
                from werkzeug.security import generate_password_hash
                import uuid
                
                # 创建管理员账户
                admin = User(
                    public_id=str(uuid.uuid4()),
                    username='admin',
                    email='admin@bioinfonexus.com',
                    password=generate_password_hash('Admin20040625'),
                    is_active=True,
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("已创建默认管理员账户 (用户名: admin, 密码: Admin20040625)")
            else:
                print(f"发现 {admin_count} 个管理员账户，无需创建默认账户")
        except Exception as e:
            print(f"尝试创建管理员账户时出错: {str(e)}")
            db.session.rollback()

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
            # 解码令牌 - 使用与auth_routes.py相同的密钥获取逻辑
            from flask import current_app
            # 获取密钥，确保与登录时使用的相同
            secret_key = current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY', 'dev_key_please_change')
            if not isinstance(secret_key, str):
                secret_key = str(secret_key)  # 转换为字符串
                
            # 输出调试信息
            print(f"token_required: 尝试使用密钥验证令牌，密钥类型: {type(secret_key)}")
            
            data = jwt.decode(token, secret_key, algorithms=['HS256'])
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