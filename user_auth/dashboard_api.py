from flask import Blueprint, jsonify
import pymysql
from datetime import datetime, timedelta
import logging
from functools import wraps
from flask import current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import calendar
import os
from dotenv import load_dotenv
from user_auth.user_system import User, db

# 加载环境变量
load_dotenv()

# 尝试导入psutil库，如果不存在，则记录错误
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logging.error("未安装psutil库，系统资源监控功能将不可用。请使用pip install psutil安装。")

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

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

# 新的管理员权限检查装饰器，配合flask_jwt_extended使用
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # 获取当前用户ID (注意此函数必须在jwt_required装饰器之后使用)
            user_id = get_jwt_identity()
            
            if not user_id:
                logging.error("JWT身份验证失败: 无法获取用户ID")
                return jsonify({"message": "身份验证失败"}), 401
            
            # 查询用户
            user = User.query.get(user_id)
            
            if not user:
                logging.error(f"管理员权限验证失败: 用户ID {user_id} 不存在")
                return jsonify({"message": "用户未找到"}), 404
                
            if not user.is_admin:
                logging.error(f"管理员权限验证失败: 用户 {user.username} (ID: {user_id}) 不是管理员")
                return jsonify({"message": "需要管理员权限"}), 403
                
            return f(*args, **kwargs)
            
        except Exception as e:
            logging.error(f"管理员权限验证错误: {str(e)}")
            return jsonify({"message": "身份验证失败"}), 401
            
    return decorated

# 获取系统资源使用情况
@dashboard_bp.route('/resource-usage', methods=['GET'])
@jwt_required()
@admin_required
def get_resource_usage():
    try:
        # 检查psutil是否可用
        if not HAS_PSUTIL:
            logging.error("系统资源监控功能不可用: psutil库未安装")
            return jsonify({"error": "未安装psutil库，系统资源监控功能不可用"}), 500
            
        # 获取CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 获取内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 获取磁盘使用率
        try:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
        except Exception as disk_error:
            logging.warning(f"获取磁盘使用率失败: {str(disk_error)}，使用默认值")
            disk_percent = 0
        
        # 获取网络使用率（这里使用一个估算值，实际应根据网络带宽计算）
        try:
            network_percent = min(psutil.net_io_counters().bytes_sent % 100, 100)
        except Exception as net_error:
            logging.warning(f"获取网络使用率失败: {str(net_error)}，使用默认值")
            network_percent = 0
        
        logging.info("系统资源使用情况获取成功")
        return jsonify({
            'cpu': round(cpu_percent, 2),
            'memory': round(memory_percent, 2),
            'disk': round(disk_percent, 2),
            'network': round(network_percent, 2)
        })
    except Exception as e:
        logging.error(f"获取系统资源使用情况失败: {str(e)}")
        return jsonify({"error": "获取系统资源使用情况失败，请检查服务器日志"}), 500

# 获取用户增长数据
@dashboard_bp.route('/user-growth', methods=['GET'])
@jwt_required()
@admin_required
def get_user_growth():
    """获取用户增长趋势数据"""
    try:
        range_param = request.args.get('range', 'month')  # 默认月视图
        
        # 获取当前日期
        today = datetime.now().date()
        
        if range_param == 'year':
            # 年度视图 - 按月统计
            result = {}
            for month in range(1, 13):
                # 获取当月开始和结束日期
                year = today.year
                start_date = datetime(year, month, 1)
                
                # 获取当月最后一天
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day, 23, 59, 59)
                
                # 如果是未来月份，跳过
                if start_date > datetime.now():
                    result[month] = 0
                    continue
                    
                # 查询当月注册用户数
                count = User.query.filter(
                    User.created_at >= start_date,
                    User.created_at <= end_date
                ).count()
                
                # 存储结果
                result[month] = count
                
            months = [
                '一月', '二月', '三月', '四月', '五月', '六月', 
                '七月', '八月', '九月', '十月', '十一月', '十二月'
            ]
            
            return jsonify({
                'labels': months,
                'data': list(result.values()),
                'total': sum(result.values())
            })
            
        elif range_param == 'month':
            # 月度视图 - 按日统计
            # 获取当月第一天
            first_day = today.replace(day=1)
            
            # 获取当月最后一天
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            
            result = {}
            for day in range(1, last_day.day + 1):
                # 设置当天的日期范围
                current_date = today.replace(day=day)
                start_date = datetime.combine(current_date, datetime.min.time())
                end_date = datetime.combine(current_date, datetime.max.time())
                
                # 如果是未来日期，跳过
                if start_date > datetime.now():
                    result[day] = 0
                    continue
                    
                # 查询当天注册用户数
                count = User.query.filter(
                    User.created_at >= start_date,
                    User.created_at <= end_date
                ).count()
                
                # 存储结果
                result[day] = count
                
            return jsonify({
                'labels': list(result.keys()),
                'data': list(result.values()),
                'total': sum(result.values())
            })
        
        # 默认返回错误
        logging.error(f"无效的时间范围参数: {range_param}")
        return jsonify({'error': '无效的时间范围参数', 'valid_ranges': ['year', 'month']}), 400
    except ValueError as ve:
        logging.error(f"用户增长数据值错误: {str(ve)}")
        return jsonify({"error": "数据处理过程中出现错误"}), 422
    except TypeError as te:
        logging.error(f"用户增长数据类型错误: {str(te)}")
        return jsonify({"error": "数据类型错误"}), 422
    except Exception as e:
        logging.error(f"获取用户增长数据失败: {str(e)}")
        return jsonify({"error": "获取用户增长数据失败，请检查服务器日志"}), 500