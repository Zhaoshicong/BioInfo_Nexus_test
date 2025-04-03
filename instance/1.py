# add_virtual_users.py - 为BioInfo Nexus系统添加虚拟用户

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import uuid
import datetime
import random
import os
import sys
from sqlalchemy import text, inspect

# 创建一个临时应用来访问数据库
app = Flask(__name__)

# 获取当前工作目录，确保路径正确
current_dir = os.getcwd()
print(f"当前工作目录: {current_dir}")

# 使用相对路径连接当前实例目录下的数据库
database_path = os.path.join(current_dir, 'instance', 'bioinfo_nexus.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"尝试连接数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)

def get_table_columns(table_name):
    """获取表的实际列名"""
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            return [col['name'] for col in inspector.get_columns(table_name)]
    except Exception as e:
        print(f"获取表结构出错: {e}")
        return []

# 先检查数据库连接和表结构
if not os.path.exists(database_path):
    print(f"错误: 数据库文件不存在: {database_path}")
    sys.exit(1)

# 定义一个更灵活的User模型类，根据实际表结构动态调整
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), nullable=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    verification_code = db.Column(db.String(10), nullable=True)
    verification_code_expiry = db.Column(db.DateTime, nullable=True)
    reset_code = db.Column(db.String(10), nullable=True)
    
    def __repr__(self):
        return f'<User {self.email}>'

def test_db_connection():
    """测试数据库连接"""
    try:
        with app.app_context():
            db.session.execute(text("SELECT 1"))
            print("数据库连接成功!")
            return True
    except Exception as e:
        print(f"数据库连接失败: {str(e)}")
        return False

def generate_users(count=50):
    """生成指定数量的虚拟用户"""
    domains = ['example.com', '163.com', 'qq.com', 'gmail.com', 'outlook.com', '126.com', 'sina.com', 'sohu.com']
    
    users_created = 0
    
    try:
        with app.app_context():
            # 获取users表的实际列名
            columns = get_table_columns('users')
            print(f"检测到的表列: {columns}")
            
            if not columns:
                print("无法获取表结构，请检查数据库连接")
                return
                
            if 'id' not in columns or 'email' not in columns:
                print("表结构缺少必要的列(id, email)，无法继续")
                return
            
            for i in range(count):
                try:
                    # 生成数字用户名
                    username_num = str(random.randint(100000, 999999999))
                    domain = random.choice(domains)
                    email = f"user{username_num}@{domain}"
                    password = generate_password_hash(f"Pass{random.randint(100, 999)}!")
                    now = datetime.datetime.now()
                    
                    # 根据实际表结构创建用户数据
                    user_data = {
                        'public_id': str(uuid.uuid4()),
                        'email': email,
                        'password': password
                    }
                    
                    # 添加检测到的其他字段
                    if 'username' in columns:
                        user_data['username'] = f"user{username_num}"
                    
                    if 'created_at' in columns:
                        user_data['created_at'] = now - datetime.timedelta(days=random.randint(0, 365))
                    
                    if 'last_login' in columns:
                        # 50%的用户有上次登录时间
                        if random.random() > 0.5:
                            user_data['last_login'] = now - datetime.timedelta(days=random.randint(0, 30))
                    
                    if 'is_active' in columns:
                        user_data['is_active'] = True
                    
                    if 'is_admin' in columns:
                        user_data['is_admin'] = False
                        
                    # 使用ORM方式添加用户
                    new_user = User(**user_data)
                    db.session.add(new_user)
                    
                    # 每5个用户提交一次
                    if (i + 1) % 5 == 0 or i == count - 1:
                        db.session.commit()
                        users_created = i + 1
                        print(f"已成功创建 {users_created} 个虚拟用户")
                
                except Exception as e:
                    print(f"创建第 {i+1} 个用户时出错: {e}")
                    db.session.rollback()
            
    except Exception as e:
        print(f"操作过程中发生错误: {e}")
        
    print(f"脚本完成。成功创建用户数: {users_created}")

if __name__ == "__main__":
    # 先测试数据库连接
    if not test_db_connection():
        print("数据库连接测试失败，请检查配置。")
        sys.exit(1)
        
    user_count = input("请输入要生成的虚拟用户数量 [默认50]: ")
    try:
        count = int(user_count) if user_count.strip() else 50
    except ValueError:
        count = 50
        print("输入无效，将使用默认值50")
    
    print(f"开始生成 {count} 个虚拟用户...")
    generate_users(count)
    print("虚拟用户生成脚本执行完毕！")