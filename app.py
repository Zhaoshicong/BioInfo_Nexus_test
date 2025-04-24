# 导入必要的环境变量加载模块
import os
from dotenv import load_dotenv

# 加载环境变量，必须在任何其他导入前执行
print("==================================================")
print("app.py: 开始加载环境变量...")
load_dotenv()
print(f"app.py: 环境变量 DB_TYPE = {os.environ.get('DB_TYPE')}")
print(f"app.py: 环境变量 MYSQL_HOST = {os.environ.get('MYSQL_HOST')}")
print(f"app.py: 环境变量 MYSQL_DB = {os.environ.get('MYSQL_DB')}")
print(f"app.py: 环境变量 SECRET_KEY 已设置 = {bool(os.environ.get('SECRET_KEY'))}")
print("==================================================")

# 以下是其他模块的导入
from flask import Flask, request, jsonify, send_from_directory, redirect
from Bio_tools.ProtParam import get_molecular_weight
from Bio_tools.SignalP import submit_sequence, extract_and_parse_results
from Bio_tools.VaxiJen import get_vaxijen_result
from Bio_tools.ToxinPred import predict_toxicity, predict_toxin
from Bio_tools.PhysChemParameter import get_PhysChemParameter
from Bio_tools.SequenceAnnotation import sequence_annotation
from Bio_tools.Translate import translate_sequence, get_available_tables
from Bio_tools.RestrictionAnalysis import analyze_restriction 
from Bio_tools.FindCuttingEnzymes import find_all_cutting_enzymes
from Bio_tools.GCContent import analyze_nucleic_acid_properties
from Bio_tools.CodonAnalyzer import analyze_sequence_codons
from Bio_tools.Transform import transform_fasta
import base64
import os
import time 
import sys
from functools import wraps
import logging
from datetime import datetime, timedelta
from flask_cors import CORS  # 导入CORS
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import re  # 添加正则表达式模块
from flask_mail import Mail  # 导入Flask-Mail
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity  # 导入JWT扩展
from user_auth.user_system import db, init_user_system
from flask_migrate import Migrate
from Bio_tools.AI_service import generate_report

# 导入用户系统
from user_auth.user_system import init_user_system, token_required, User, db
from user_auth.auth_routes import auth_bp, mail
from user_auth.admin_routes import admin_bp
from user_auth.dashboard_api import dashboard_bp
from user_auth.membership_routes import membership_bp  # 导入会员模块蓝图

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
app_secret_key = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')

# 确保密钥是字符串
if not isinstance(app_secret_key, str):
    app_secret_key = str(app_secret_key)

# 设置密钥
app.config['SECRET_KEY'] = app_secret_key
app.config['JWT_SECRET_KEY'] = app_secret_key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
app.config['JWT_IDENTITY_CLAIM'] = 'sub'  # 确保身份声明与MySQL中的ID字段匹配
app.config['JWT_ERROR_MESSAGE_KEY'] = 'message'  # 自定义错误消息字段
app.config['JWT_BLACKLIST_ENABLED'] = True  # 启用黑名单（如果您使用黑名单）
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']  # 只检查访问令牌

# 打印JWT配置信息
print("=" * 50)
print(f"JWT配置: SECRET_KEY 类型={type(app.config['SECRET_KEY'])}, JWT_SECRET_KEY 类型={type(app.config['JWT_SECRET_KEY'])}")
print(f"密钥一致性检查: SECRET_KEY == JWT_SECRET_KEY: {app.config['SECRET_KEY'] == app.config['JWT_SECRET_KEY']}")
print("=" * 50)

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
app.register_blueprint(dashboard_bp)
app.register_blueprint(membership_bp)  # 注册会员模块蓝图

# 添加静态文件服务路由，用于访问temp目录中的图像
@app.route('/temp/<path:filename>')
def serve_temp_file(filename):
    return send_from_directory('temp', filename)

# 添加上传文件服务路由
@app.route('/uploads/<path:filename>')
def serve_upload_file(filename):
    return send_from_directory('uploads', filename)

# 添加Bio_tools数据文件服务路由
@app.route('/Bio_tools/data/<path:filename>')
def serve_biotools_data(filename):
    return send_from_directory('Bio_tools/data', filename)

# 添加管理员登录页面路由
@app.route('/admin-login')
def admin_login_page():
    return app.send_static_file('admin-login.html')

# 添加管理面板页面路由
@app.route('/admin-panel')
def admin_panel_page():
    return app.send_static_file('admin.html')

def validate_sequence(sequence, seq_type=None):
    """验证序列的有效性，支持蛋白质、DNA和RNA序列"""
    sequence = sequence.upper().replace(' ', '')
    
    # 有效字符集
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
    valid_dna = set('ATGC')
    valid_rna = set('AUGC')
    
    # 尝试自动检测序列类型
    if not seq_type:
        if all(base in valid_dna for base in sequence):
            return True  # 有效的DNA序列
        elif all(base in valid_rna for base in sequence):
            return True  # 有效的RNA序列
        else:
            return all(aa in valid_aa for aa in sequence)  # 检查是否为有效的蛋白质序列
    
    # 如果指定了序列类型
    if seq_type.lower() == 'protein':
        return all(aa in valid_aa for aa in sequence)
    elif seq_type.lower() == 'dna':
        return all(base in valid_dna for base in sequence)
    elif seq_type.lower() == 'rna':
        return all(base in valid_rna for base in sequence)
    else:
        # 未知序列类型，使用自动检测
        return validate_sequence(sequence)

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
        # 使用与auth_routes.py相同的密钥获取逻辑
        secret_key = app.config.get('JWT_SECRET_KEY') or app.config.get('SECRET_KEY', 'dev_key_please_change')
        if not isinstance(secret_key, str):
            secret_key = str(secret_key)  # 转换为字符串
            
        # 解码令牌
        data = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = data.get('public_id')
        
        if not user_id:
            logger.error("解码令牌时出错: 令牌中没有public_id")
            return None
            
        return User.query.filter_by(public_id=user_id).first()
    except Exception as e:
        logger.error(f"解码令牌时出错: {str(e)}")
        return None
    
@app.route('/api/transform', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def transform_api(current_user):
    """通用序列格式转换API
    
    当前支持的转换类型:
    - FASTA格式转换为纯序列
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    
    # 记录请求
    logger.info(f"用户 {current_user.username} 请求序列格式转换")
    
    # 提取序列和选项
    sequence_data = data.get('sequence')
    options = {
        'format_output': data.get('format_output', True),
        'return_all': data.get('return_all', False)
    }
    
    # 验证序列数据
    if not sequence_data:
         return jsonify({'error': '未提供序列数据'}), 400

    # 调用transform_fasta主函数处理请求，传递整个 data 字典
    result = transform_fasta(data)
    
    # 如果处理失败，返回错误信息
    if not result.get('success', False):
        return jsonify({'error': result.get('error', '未知错误')}), 400
    
    # 返回处理结果
    return jsonify(result)

@app.route('/api/protparam', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_protparam(current_user):
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
        'sequence_type': result['sequence_type'],
        'amino_acid_composition': result['amino_acid_composition'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/sequence_annotation', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_sequence_annotation(current_user):
    """分析蛋白质序列的功能注释和特征预测"""
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    
    # 记录请求
    logger.info(f"用户 {current_user.username} 请求序列注释分析，序列长度: {len(sequence)}")
    
    # 调用SequenceAnnotation模块
    try:
        result = sequence_annotation(sequence)
        
        if "error" in result:
            return jsonify({'error': result["error"]}), 500
        
        # 标记成功
        result['success'] = True
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"序列注释分析错误: {str(e)}")
        return jsonify({'error': f'分析过程发生错误: {str(e)}'}), 500
    
@app.route('/api/translate', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_translate(current_user):
    """翻译DNA/RNA序列为蛋白质序列"""
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    seq_type = data.get('seq_type')  # 可以是 'dna' 或 'rna'，如果未提供则自动检测
    table_id = data.get('table_id', 1)  # 遗传密码表ID，默认为1
    to_stop = data.get('to_stop', False)  # 是否在第一个终止密码子处停止翻译
    cds = data.get('cds', False)  # 是否将序列视为完整的编码序列
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    
    # 记录请求
    logger.info(f"用户 {current_user.username} 请求序列翻译，序列长度: {len(sequence)}")
    
    # 调用Translate模块
    try:
        result = translate_sequence(sequence, seq_type, table_id, to_stop, cds)
        
        if "error" in result:
            return jsonify({'error': result["error"]}), 500
        
        # 获取可用的遗传密码表信息
        tables = get_available_tables()
        
        # 添加到结果中
        result['available_tables'] = tables
        result['success'] = True
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"序列翻译错误: {str(e)}")
        return jsonify({'error': f'翻译过程发生错误: {str(e)}'}), 500
    
@app.route('/api/analyze_codons', methods=['POST', 'GET'])
@error_handler
#@rate_limit
@token_required
def analyze_codons(current_user):
    """密码子分析API接口
    
    GET方法: 获取可用的宿主物种列表
    POST方法: 分析DNA/RNA序列的密码子使用情况，或通过action=list_hosts获取宿主列表
    """
    # 记录请求
    logger.info(f"用户 {current_user.username} 请求密码子分析API")
    
    # 处理获取可用宿主列表请求
    if request.method == 'GET' or (request.method == 'POST' and request.get_json().get('action') == 'list_hosts'):
        try:
            # 确定数据目录的路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, "Bio_tools", "data", "codon_tables")
            
            # 检查目录是否存在
            if not os.path.exists(data_dir):
                return jsonify({
                    'error': '找不到宿主数据目录',
                    'message': f'目录 {data_dir} 不存在'
                }), 500
            
            # 直接扫描目录中的所有JSON文件，提取物种ID
            available_hosts = []
            for filename in os.listdir(data_dir):
                if filename.endswith('.json') and filename != "species_map.json":
                    # 提取物种ID（文件名不含扩展名）
                    host_id = os.path.splitext(filename)[0]
                    
                    # 直接使用物种ID作为名称
                    available_hosts.append({
                        'host_id': host_id,
                        'genetic_code_id': 1,  # 使用标准密码表
                        'name': f'物种ID: {host_id}'
                    })
            
            # 按照host_id排序，方便用户查找
            available_hosts.sort(key=lambda x: x['host_id'])
            
            return jsonify({
                'success': True,
                'available_hosts': available_hosts
            })
        
        except Exception as e:
            logger.error(f"获取可用宿主列表错误: {str(e)}")
            return jsonify({'error': f'获取宿主列表时发生错误: {str(e)}'}), 500
    
    # 处理密码子分析请求
    if request.method == 'POST':
        data = request.get_json()
        
        # 如果没有指定action或action为analyze，则执行分析
        if data.get('action', 'analyze') == 'analyze':
            sequence = data.get('sequence')
            host_id = data.get('host_id')  # 宿主物种的ID
            rarity_threshold = data.get('rarity_threshold', 0.05)  # 稀有密码子阈值，默认为0.05
            
            # 输入验证
            if not sequence:
                return jsonify({'error': '序列不能为空'}), 400
            
            if not host_id:
                return jsonify({'error': '宿主ID不能为空'}), 400
                
            # 使用默认遗传密码表ID
            genetic_code_id = 1  # 标准遗传密码表
            
            # 确保参数类型正确
            try:
                rarity_threshold = float(rarity_threshold)
            except (ValueError, TypeError):
                return jsonify({'error': '稀有密码子阈值必须为浮点数'}), 400
            
            # 记录请求
            logger.info(f"用户 {current_user.username} 请求密码子分析，序列长度: {len(sequence)}，宿主ID: {host_id}，使用密码表ID: {genetic_code_id}")
            
            # 调用CodonAnalyzer模块
            try:
                result = analyze_sequence_codons(sequence, host_id, genetic_code_id, rarity_threshold)
                
                # 检查分析结果状态
                if result.get('status') == 'error':
                    return jsonify({'error': result.get('message', '分析过程中发生错误')}), 500
                
                # 添加成功标志
                result['success'] = True
                result['sequence'] = sequence
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"密码子分析错误: {str(e)}")
                return jsonify({'error': f'分析过程发生错误: {str(e)}'}), 500
    
    # 如果代码执行到这里，说明请求不符合任何处理条件
    return jsonify({'error': '不支持的请求格式或操作'}), 400
    
@app.route('/api/find_cutting_enzymes', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def handle_find_cutting_enzymes(current_user):
    """处理查找所有切割酶的请求"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空', 'message': '需要提供JSON数据'}), 400

    sequence = data.get('sequence')

    if not sequence:
        return jsonify({'error': '缺少序列', 'message': '需要提供DNA序列'}), 400

    # 调用查找函数
    result = find_all_cutting_enzymes(sequence)

    # 如果函数返回错误，将其传递给前端
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': '查找过程中出错'}), 400 # 或 500

    return jsonify(result)

@app.route('/api/analyze_restriction', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def handle_analyze_restriction(current_user):
    """处理限制性内切酶分析请求"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空', 'message': '需要提供JSON数据'}), 400

    sequence = data.get('sequence')
    enzymes_str = data.get('enzymes') # 接收用空格分隔的酶名称字符串

    if not sequence:
        return jsonify({'error': '缺少序列', 'message': '需要提供DNA序列'}), 400
    if not enzymes_str:
        return jsonify({'error': '缺少酶名称', 'message': '需要提供至少一个限制酶名称'}), 400

    # 清理和分割酶名称
    enzyme_names = [name.strip() for name in enzymes_str.split() if name.strip()]
    if not enzyme_names:
         return jsonify({'error': '无效的酶名称格式', 'message': '请提供有效的、用空格分隔的酶名称'}), 400

    # 调用分析函数
    result = analyze_restriction(sequence, enzyme_names)

    # 如果分析函数返回错误，将其传递给前端
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': '分析过程中出错'}), 400 # 或者 500，取决于错误类型

    return jsonify(result)

@app.route('/api/analyze_nucleic_acid', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_nucleic_acid(current_user):
    """分析核酸序列的物理化学特性，包括GC含量、熔解温度和浮力密度"""
    data = request.get_json()
    sequence = data.get('sequence', '').strip().upper()
    sequence_type = data.get('sequence_type', 'dna')  # dna, ssdna, rna
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    
    # 验证序列类型
    if sequence_type not in ['dna', 'ssdna', 'rna']:
        return jsonify({'error': '序列类型必须是 dna, ssdna 或 rna'}), 400
    
    # 记录请求
    logger.info(f"用户 {current_user.username} 请求核酸物理化学特性分析，序列长度: {len(sequence)}")
    
    try:
        # 调用分析函数
        result = analyze_nucleic_acid_properties(sequence)
        
        if "error" in result:
            return jsonify({'error': result["error"]}), 500
        
        # 添加序列类型信息
        result['sequence_type'] = sequence_type
        result['success'] = True
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"核酸物理化学特性分析错误: {str(e)}")
        return jsonify({'error': f'分析过程发生错误: {str(e)}'}), 500

@app.route('/api/signalp', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_signalp(current_user):
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
                    'sequence': sequence,
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
                    'sequence': sequence,
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
#@rate_limit
@token_required
def analyze_vaxijen(current_user):
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
    
    # 判断是否为抗原
    is_antigen = result.lower() == 'antigen' or 'antigen' in result.lower()
    
    response_data = {
        'sequence': sequence,
        'result': result,
        'score': probability,
        'is_antigen': is_antigen,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(response_data)

@app.route('/api/toxinpred', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_toxinpred(current_user):
    """分析肽的毒性"""
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    if not validate_sequence(sequence):
        return jsonify({'error': '无效的氨基酸序列'}), 400
    
    # 序列长度检查
    if len(sequence) < 5 or len(sequence) > 50:
        return jsonify({'error': '序列长度应在5-50个氨基酸之间'}), 400
    
    # 记录请求
    logger.info(f"ToxinPred分析请求 - 序列长度: {len(sequence)}")
    
    # 确保temp目录存在
    os.makedirs('temp', exist_ok=True)
    
    # 调用ToxinPred模块
    try:
        # 尝试使用旧函数
        try:
            simple_results = predict_toxin(sequence, verbose=True)
            logger.info(f"从predict_toxin获取结果: {simple_results}")
            
            # 如果旧函数成功
            if simple_results and simple_results.get('success') and simple_results.get('results'):
                result_item = simple_results['results'][0]
                
                response_data = {
                    'sequence': sequence,
                    'result': result_item.get('Prediction', '未知'),
                    'svm_score': result_item.get('SVM Score', '未知'),
                    'is_toxin': result_item.get('Prediction', '').lower() == "toxin" or "toxin" in result_item.get('Prediction', '').lower(),
                    'toxicity_features': {
                        'Hydrophobicity': result_item.get('Hydrophobicity', '未知'),
                        'Hydropathicity': result_item.get('Hydropathicity', '未知'),
                        'Hydrophilicity': result_item.get('Hydrophilicity', '未知'),
                        'Charge': result_item.get('Charge', '未知'),
                        'Mol wt': result_item.get('Mol wt', '未知')
                    },
                    'success': True
                }
                
                return jsonify(response_data)
        except Exception as e:
            logger.warning(f"使用旧函数predict_toxin失败: {str(e)}")
        
        # 如果旧函数失败，尝试使用新函数
        result = predict_toxicity(sequence)
        
        if not result:
            return jsonify({'error': '无法获取预测结果'}), 500
        
        response_data = {
            'sequence': sequence,
            'result': result.get('result', '未知'),
            'is_toxin': result.get('is_toxin', False),
            'svm_score': result.get('svm_score', '未知'),
            'toxicity_features': result.get('features', {}),
            'success': True
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"ToxinPred分析错误: {str(e)}")
        return jsonify({'error': f'分析过程发生错误: {str(e)}'}), 500

@app.route('/api/physchemparam', methods=['POST'])
@error_handler
#@rate_limit
@token_required
def analyze_physchemparam(current_user):
    """分析蛋白质物理化学参数"""
    data = request.get_json()
    sequence = data.get('sequence', '').strip()
    
    # 输入验证
    if not sequence:
        return jsonify({'error': '序列不能为空'}), 400
    if not validate_sequence(sequence):
        return jsonify({'error': '无效的氨基酸序列'}), 400
    
    # 记录请求
    logger.info(f"用户 {current_user.username} 请求物理化学参数分析，序列长度: {len(sequence)}")
    
    # 调用PhysChemParameter模块
    try:
        result = get_PhysChemParameter(sequence)
        
        if "error" in result:
            return jsonify({'error': result["error"]}), 500
        
        # 记录分析历史 - 暂时注释掉以避免导入错误
        # from user_auth.user_system import AnalysisHistory, db
        # history = AnalysisHistory(
        #     user_id=current_user.id,
        #     tool_name='physchemparam',
        #     sequence=sequence,
        #     result=f"分子量: {result.get('molecular_weight', '未知')}, 理论pI: {result.get('theoretical_pi', '未知')}"
        # )
        # db.session.add(history)
        # db.session.commit()
        
        # 原样返回完整结果
        result['sequence'] = sequence
        result['success'] = True
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"PhysChemParameter分析错误: {str(e)}")
        return jsonify({'error': f'分析过程发生错误: {str(e)}'}), 500

# 添加JWT错误处理
@jwt.unauthorized_loader
def unauthorized_callback(callback):
    logging.error(f"JWT未授权: {callback}")
    return jsonify({
        'message': '缺少有效的认证令牌',
        'error': 'authorization_required'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(callback):
    logging.error(f"JWT无效令牌: {callback}")
    return jsonify({
        'message': '认证令牌无效',
        'error': 'invalid_token'
    }), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    logging.error(f"JWT令牌过期: {jwt_payload}")
    return jsonify({
        'message': '认证令牌已过期',
        'error': 'token_expired'
    }), 401

# AI分析端点
@app.route('/api/ai_analyze', methods=['POST'])
@error_handler
@token_required
def ai_analyze(current_user):
    """
    使用AI分析序列并根据用户需求生成报告
    请求格式:
    {
        "sequence": "序列内容",
        "query": "用户的自然语言查询/需求",
        "tool": "工具名称"  // 可选，如果未指定，将自动选择合适的工具
    }
    """
    logger.info("收到AI分析请求")
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    sequence = data.get("sequence", "").strip().upper()
    user_query = data.get("query", "").strip()
    tool = data.get("tool", "")
    
    if not sequence:
        return jsonify({"error": "序列不能为空"}), 400
    
    if not user_query:
        return jsonify({"error": "分析需求不能为空"}), 400
    
    try:
        # 首先使用指定的工具或自动选择工具进行分析
        tool_results = {}
        
        # 检测序列类型以选择适当的工具
        dna_pattern = re.compile(r'^[ATGC]+$')
        rna_pattern = re.compile(r'^[AUGC]+$')
        protein_pattern = re.compile(r'^[ACDEFGHIKLMNPQRSTVWY]+$')
        
        detected_type = "unknown"
        if dna_pattern.match(sequence):
            detected_type = "dna"
        elif rna_pattern.match(sequence):
            detected_type = "rna"
        elif protein_pattern.match(sequence):
            detected_type = "protein"
        
        # 如果未指定工具，根据序列类型自动选择工具
        if not tool:
            if detected_type == "protein":
                # 为蛋白质序列选择合适的工具
                tools = ["protparam", "sequence_annotation", "physchemparam"]
            elif detected_type == "dna":
                # 为DNA序列选择合适的工具
                tools = ["analyze_nucleic_acid", "find_cutting_enzymes", "translate"]
            elif detected_type == "rna":
                # 为RNA序列选择合适的工具
                tools = ["analyze_nucleic_acid", "translate"]
            else:
                return jsonify({"error": "无法确定序列类型，请指定工具"}), 400
        else:
            # 使用用户指定的工具
            tools = [tool]
        
        # 对每个工具执行分析
        for tool_name in tools:
            try:
                if tool_name == "protparam":
                    result = get_molecular_weight(sequence)
                elif tool_name == "sequence_annotation":
                    result = sequence_annotation(sequence)
                elif tool_name == "physchemparam":
                    result = get_PhysChemParameter(sequence)
                elif tool_name == "analyze_nucleic_acid":
                    result = analyze_nucleic_acid_properties(sequence)
                elif tool_name == "find_cutting_enzymes":
                    result = find_all_cutting_enzymes(sequence)
                elif tool_name == "translate":
                    result = translate_sequence(sequence)
                elif tool_name == "toxinpred":
                    result = predict_toxin(sequence)
                elif tool_name == "vaxijen":
                    result = get_vaxijen_result(sequence)
                elif tool_name == "signalp  ":
                    result = analyze_signalp(sequence)
                else:
                    logger.warning(f"未知工具: {tool_name}")
                    continue
                
                # 将工具分析结果添加到结果集
                tool_results[tool_name] = result
                
            except Exception as e:
                logger.error(f"工具 {tool_name} 分析错误: {str(e)}")
                tool_results[tool_name] = {"error": str(e)}
        
        # 如果没有任何工具返回结果，返回错误
        if not tool_results:
            return jsonify({"error": "所有工具分析均失败"}), 500
        
        # 使用AI服务生成报告
        ai_result = generate_report(tool_results, user_query)
        
        # 检查AI服务是否成功
        if not ai_result.get("success", False):
            return jsonify({
                "error": ai_result.get("error", "AI服务处理失败"),
                "tool_results": tool_results  # 仍然返回工具结果
            }), 500
        
        # 返回完整的AI分析结果
        return jsonify({
            "success": True,
            "report": ai_result.get("report", ""),
            "tool_results": tool_results,
            "user_query": user_query,
            "sequence": sequence,
            "detected_type": detected_type
        })
        
    except Exception as e:
        logger.error(f"AI分析处理错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 确保临时文件目录存在
    os.makedirs('temp', exist_ok=True)
    
    # 确保上传文件目录存在
    os.makedirs('uploads/avatars', exist_ok=True)
    
    # 配置应用
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制请求大小为16MB
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # 设置递归深度限制
    sys.setrecursionlimit(3000)  # 设置更高的值，默认通常是1000
    
    # 开发环境运行方式
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,
        debug=True,     # 开发环境开启调试模式
        threaded=True    # 启用多线程
    )