from flask import Flask, request, jsonify, send_from_directory, redirect
from Bio_tools.ProtParam import get_molecular_weight
from Bio_tools.SignalP import submit_sequence, extract_and_parse_results
from Bio_tools.VaxiJen import get_vaxijen_result
import base64
import os
import time
from functools import wraps
import logging
from datetime import datetime, timedelta
from flask_cors import CORS  # 导入CORS
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import re  # 添加正则表达式模块
from flask_mail import Mail  # 导入Flask-Mail
from dotenv import load_dotenv  # 导入dotenv
from flask_jwt_extended import JWTManager  # 导入JWT扩展
from user_auth.user_system import db, init_user_system
from flask_migrate import Migrate

# 加载环境变量
load_dotenv()

# 导入用户系统
from user_auth.user_system import init_user_system, token_required, User, db
from user_auth.auth_routes import auth_bp, mail
from user_auth.admin_routes import admin_bp

# 配置日志
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='front_html', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})  # 明确指定允许的方法

# 配置JWT
app.config['JWT_SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# 初始化JWT
jwt = JWTManager(app)

# 配置邮件服务
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = 465  # 直接使用465端口
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False').lower() in ('true', 'yes', '1')
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', 'yes', '1')
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
app.config['MAIL_ASCII_ATTACHMENTS'] = False
app.config['MAIL_CHARSET'] = 'utf-8'

# 初始化邮件服务
mail.init_app(app)

# 初始化用户系统
init_user_system(app)

# 初始化数据库迁移
migrate = Migrate(app, db)

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')

# 添加静态文件服务路由，用于访问temp目录中的图像
@app.route('/temp/<path:filename>')
def serve_temp_file(filename):
    return send_from_directory('temp', filename)

# 添加上传文件服务路由
@app.route('/uploads/<path:filename>')
def serve_upload_file(filename):
    return send_from_directory('uploads', filename)

# 添加管理员登录页面路由
@app.route('/admin-login')
def admin_login_page():
    return app.send_static_file('admin-login.html')

# 添加管理面板页面路由
@app.route('/admin-panel')
def admin_panel_page():
    return app.send_static_file('admin.html')

# 添加一个路由处理旧的验证链接格式
@app.route('/verify_email')
def verify_email_handler():
    token = request.args.get('token')
    if not token:
        return redirect("/")
    
    # 直接在这里处理验证逻辑，而不是重定向
    from user_auth.user_system import User, db
    
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        # 验证失败，返回错误页面
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
    
    # 验证成功，更新用户状态
    user.is_active = True
    user.verification_token = None
    db.session.commit()
    
    # 返回成功页面
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

def validate_sequence(sequence):
    """验证氨基酸序列的有效性"""
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    sequence = sequence.upper().replace(' ', '')
    return all(aa in valid_aa for aa in sequence)

def error_handler(func):
    """错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return jsonify({
                'error': str(e),
                'message': '服务器处理请求时发生错误'
            }), 500
    return wrapper

# 请求限制装饰器
def rate_limit(func):
    requests = {}
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        # 清理旧的请求记录
        requests[ip] = [t for t in requests.get(ip, []) if current_time - t < 60]
        
        # 检查请求频率（每分钟最多10次）
        if len(requests.get(ip, [])) >= 10:
            return jsonify({
                'error': '请求过于频繁',
                'message': '请稍后再试'
            }), 429
        
        # 记录新的请求
        requests.setdefault(ip, []).append(current_time)
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/search')
def search():
    return app.send_static_file('search.html')

# 修改API端点，添加用户历史记录功能
@app.route('/api/protparam', methods=['POST'])
@error_handler
@rate_limit
def analyze_protparam():
    """分析蛋白质分子量"""
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    if not validate_sequence(sequence):
        return jsonify({'error': '无效的氨基酸序列'}), 400
        
    # 记录请求
    logger.info(f"ProtParam analysis request - Sequence length: {len(sequence)}")
    
    # 执行分析
    result = get_molecular_weight(sequence)
    
    if 'error' in result:
        return jsonify(result), 400
        
    return jsonify({
        'molecular_weight': result['molecular_weight'],
        'sequence': result['sequence'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/signalp', methods=['POST'])
@error_handler
@rate_limit
def analyze_signalp():
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    if not validate_sequence(sequence):
        return jsonify({'error': '无效的氨基酸序列'}), 400
    
    # 确保temp目录存在
    os.makedirs('temp', exist_ok=True)
    
    # 记录请求
    logger.info(f"SignalP analysis request - Sequence length: {len(sequence)}")
    
    # 提交序列 - 最多尝试3次
    max_submit_attempts = 3
    jobid = None
    session = None
    
    for attempt in range(max_submit_attempts):
        try:
            logger.info(f"提交序列尝试 {attempt+1}/{max_submit_attempts}")
            jobid, session = submit_sequence(sequence)
            if jobid:
                logger.info(f"成功获取JobID: {jobid}")
                break
            else:
                logger.warning(f"获取JobID失败，等待5秒后重试...")
                time.sleep(5)
        except Exception as e:
            logger.error(f"提交序列时发生错误: {str(e)}")
            if attempt < max_submit_attempts - 1:
                time.sleep(5)
            
    if not jobid:
        return jsonify({'error': '无法获取JobID，请稍后重试'}), 500
    
    # 获取结果
    try:
        logger.info(f"开始获取JobID {jobid} 的结果")
        result = extract_and_parse_results(jobid, session)
        
        if result["success"]:
            image_path = result.get("image_path")
            result_text = result.get("result_text", "无详细预测文本")
            
            # 如果有图像路径且文件存在
            if image_path and os.path.exists(image_path):
                # 创建图像URL - 使用相对路径，确保以/开头
                if not image_path.startswith('/'):
                    image_url = f"/{image_path}"
                else:
                    image_url = image_path
                
                logger.info(f"成功处理JobID {jobid} 的结果，包含图像: {image_url}")
                
                response_data = {
                    'success': True,
                    'image': image_url,
                    'result_text': result_text,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response_data)
            # 如果没有图像路径或文件不存在，但有结果文本
            elif result_text and result_text != "无详细预测文本":
                # 只返回文本结果
                logger.info(f"成功处理JobID {jobid} 的结果，无图像")
                
                response_data = {
                    'success': True,
                    'result_text': result_text,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(response_data)
            else:
                # 如果既没有图像也没有有效的结果文本
                logger.error("未找到任何图像文件和有效结果文本")
                return jsonify({
                    'success': False,
                    'error': '无法生成预测图像和结果文本'
                }), 500
        else:
            error_msg = result.get('error', '分析过程中发生错误')
            logger.error(f"处理结果失败: {error_msg}")
            
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
    except Exception as e:
        logger.error(f"SignalP分析过程中发生异常: {str(e)}")
        
        return jsonify({
            'success': False, 
            'error': f'分析过程中发生错误: {str(e)}'
        }), 500

@app.route('/api/vaxijen', methods=['POST'])
@error_handler
@rate_limit
def analyze_vaxijen():
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    if not validate_sequence(sequence):
        return jsonify({'error': '无效的氨基酸序列'}), 400
    
    # 记录请求
    logger.info(f"VaxiJen analysis request - Sequence length: {len(sequence)}")
    
    # 执行分析
    result, probability = get_vaxijen_result(sequence)
    
    if not result or not probability:
        return jsonify({'error': '无法获取预测结果'}), 500
    
    response_data = {
        'result': result,
        'probability': probability,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(response_data)

@app.route('/api/delete_temp_file', methods=['POST'])
@error_handler
def delete_temp_file():
    """删除指定的临时文件"""
    data = request.get_json()
    file_path = data.get('file_path', '')
    
    # 安全检查：确保文件路径在temp目录中
    if not file_path or not file_path.startswith('/temp/') or '..' in file_path:
        return jsonify({'success': False, 'error': '无效的文件路径'}), 400
    
    # 从路径中提取文件名
    file_name = os.path.basename(file_path)
    
    # 移除URL参数（如果有）
    file_name = re.sub(r'\?.*$', '', file_name)
    
    # 构建完整的文件路径
    full_path = os.path.join(os.getcwd(), 'temp', file_name)
    
    try:
        # 检查文件是否存在
        if os.path.exists(full_path):
            # 删除文件
            os.remove(full_path)
            logger.info(f"已删除临时文件: {full_path}")
            return jsonify({'success': True, 'message': f'文件 {file_name} 已删除'})
        else:
            logger.warning(f"尝试删除不存在的文件: {full_path}")
            return jsonify({'success': False, 'error': '文件不存在'})
    except Exception as e:
        logger.error(f"删除文件时出错: {str(e)}")
        return jsonify({'success': False, 'error': f'删除文件时出错: {str(e)}'}), 500

# 健康检查端点
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# 公开的用户统计API
@app.route('/api/public-stats')
def get_public_stats():
    """获取公开的用户统计信息"""
    try:
        # 获取用户总数
        total_users = User.query.count()
        
        # 获取活跃用户数
        active_users = User.query.filter_by(is_active=True).count()
        
        # 获取今日注册用户数
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.time.min)
        today_end = datetime.combine(today, datetime.time.max)
        today_users = User.query.filter(
            User.created_at >= today_start,
            User.created_at <= today_end
        ).count()
        
        # 构建统计数据
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'today_users': today_users
        }
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"获取公开统计数据失败: {str(e)}")
        return jsonify({'error': '获取统计数据失败'}), 500

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '未找到请求的资源'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    # 记录详细错误日志
    logger.error(f"405错误: {request.method} {request.path} - {error}")
    
    # 获取该路由允许的方法
    allowed_methods = error.get_response().headers.get('Allow', '未知')
    
    # 返回更详细的错误信息
    return jsonify({
        'error': '不支持的请求方法',
        'message': f'路径 {request.path} 不支持 {request.method} 方法',
        'allowed_methods': allowed_methods
    }), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

# 辅助函数：获取当前登录用户
def get_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    
    try:
        from flask_jwt_extended import decode_token
        
        # 使用flask_jwt_extended解码令牌
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        return User.query.filter_by(id=user_id).first()
    except Exception as e:
        logger.error(f"解码令牌时出错: {str(e)}")
        return None

if __name__ == '__main__':
    # 确保临时文件目录存在
    os.makedirs('temp', exist_ok=True)
    
    # 确保上传文件目录存在
    os.makedirs('uploads/avatars', exist_ok=True)
    
    # 配置应用
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制请求大小为16MB
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # 开发环境运行方式
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,
        debug=True,     # 开发环境开启调试模式
        threaded=True    # 启用多线程
    ) 