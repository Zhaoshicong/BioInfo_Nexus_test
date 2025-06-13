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
    db_host = os.environ.get('MYSQL_HOST')
    db_user = os.environ.get('MYSQL_USER')
    db_password = os.environ.get('MYSQL_PASSWORD')
    db_name = os.environ.get('MYSQL_DB')
    db_port = int(os.environ.get('MYSQL_PORT'))

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
            cumulative_users = {}

            # 获取所有月份的标签
            months = [
                '一月', '二月', '三月', '四月', '五月', '六月',
                '七月', '八月', '九月', '十月', '十一月', '十二月'
            ]

            # 只处理到当前月份
            current_month = today.month

            # 获取所有用户及其注册时间
            all_users = User.query.order_by(User.created_at).all()
            total_count = len(all_users)

            # 如果没有用户，创建模拟数据以显示曲线
            if total_count == 0:
                # 每个月都设置为0，确保曲线可见
                for month in range(1, current_month + 1):
                    result[month] = 0
                    cumulative_users[month] = 0
            else:
                # 初始化每个月的用户数为0
                for month in range(1, current_month + 1):
                    result[month] = 0

                # 根据用户注册时间统计每个月的新增用户数
                for user in all_users:
                    if user.created_at and user.created_at.year == today.year:
                        user_month = user.created_at.month
                        if 1 <= user_month <= current_month:
                            result[user_month] += 1

                # 计算累计用户数
                cumulative_count = 0
                for month in range(1, current_month + 1):
                    cumulative_count += result[month]
                    cumulative_users[month] = cumulative_count

            # 只返回到当前月份的数据
            filtered_labels = months[:current_month]
            filtered_data = list(cumulative_users.values())

            return jsonify({
                'labels': filtered_labels,
                'data': filtered_data,
                'total': sum(result.values()),
                'total_users': filtered_data  # 添加累计用户数数据
            })

        elif range_param == 'month':
            # 月度视图 - 按日统计
            # 获取当月第一天
            first_day = today.replace(day=1)

            # 获取当前日期
            current_day = today.day

            result = {}
            cumulative_users = {}

            # 获取所有用户及其注册时间
            all_users = User.query.order_by(User.created_at).all()
            total_count = len(all_users)

            # 如果没有用户，创建模拟数据以显示曲线
            if total_count == 0:
                # 每天都设置为0
                for day in range(1, current_day + 1):
                    result[day] = 0
                    cumulative_users[day] = 0
            else:
                # 初始化每天的用户数为0
                for day in range(1, current_day + 1):
                    result[day] = 0

                # 根据用户注册时间统计每天的新增用户数
                for user in all_users:
                    if user.created_at and user.created_at.year == today.year and user.created_at.month == today.month:
                        user_day = user.created_at.day
                        if 1 <= user_day <= current_day:
                            result[user_day] += 1

                # 计算累计用户数
                cumulative_count = 0
                for day in range(1, current_day + 1):
                    cumulative_count += result[day]
                    cumulative_users[day] = cumulative_count

            return jsonify({
                'labels': list(cumulative_users.keys()),
                'data': list(cumulative_users.values()),
                'total': User.query.count(),
                'total_users': list(cumulative_users.values())  # 添加累计用户数数据
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

# 获取每日登录人数数据
@dashboard_bp.route('/daily-logins', methods=['GET'])
@jwt_required()
@admin_required
def get_daily_logins():
    """获取每日登录人数趋势数据"""
    try:
        from user_auth.user_system import LoginRecord
        from sqlalchemy import func, extract
        
        range_param = request.args.get('range', 'month')  # 默认月视图

        # 获取当前日期
        today = datetime.now().date()

        if range_param == 'year':
            # 年度视图 - 按月统计
            login_stats = {}
            
            # 获取所有月份的标签
            months = [
                '一月', '二月', '三月', '四月', '五月', '六月',
                '七月', '八月', '九月', '十月', '十一月', '十二月'
            ]

            # 只处理到当前月份
            current_month = today.month
            
            # 初始化每个月的登录人数为0
            for month in range(1, current_month + 1):
                login_stats[month] = 0
                
            # 使用登录记录表统计每月独立登录用户数
            current_year_start = datetime(today.year, 1, 1)
            current_year_end = datetime(today.year, current_month + 1, 1) if current_month < 12 else datetime(today.year + 1, 1, 1)
            
            # 查询今年的登录记录，按月份和用户ID分组，统计每月独立登录用户数
            monthly_login_counts = db.session.query(
                extract('month', LoginRecord.login_time).label('month'),
                func.count(func.distinct(LoginRecord.user_id)).label('unique_users')
            ).filter(
                LoginRecord.login_time >= current_year_start,
                LoginRecord.login_time < current_year_end
            ).group_by(
                extract('month', LoginRecord.login_time)
            ).all()
            
            # 将查询结果填入统计字典
            for month_num, unique_users in monthly_login_counts:
                if 1 <= month_num <= current_month:
                    login_stats[int(month_num)] = unique_users
            
            # 只返回到当前月份的数据
            filtered_labels = months[:current_month]
            filtered_data = [login_stats[month] for month in range(1, current_month + 1)]
            
            return jsonify({
                'labels': filtered_labels,
                'data': filtered_data,
                'total': sum(login_stats.values())
            })
            
        elif range_param == 'month':
            # 月度视图 - 按日统计
            login_stats = {}
            
            # 获取当前日期
            current_day = today.day
            
            # 初始化每天的登录人数为0
            for day in range(1, current_day + 1):
                login_stats[day] = 0
                
            # 使用登录记录表统计每日独立登录用户数
            current_month_start = datetime(today.year, today.month, 1)
            current_month_end = datetime(today.year, today.month, current_day + 1) if current_day < 31 else datetime(today.year, today.month + 1, 1) if today.month < 12 else datetime(today.year + 1, 1, 1)
            
            # 查询本月的登录记录，按日期和用户ID分组，统计每日独立登录用户数
            daily_login_counts = db.session.query(
                extract('day', LoginRecord.login_time).label('day'),
                func.count(func.distinct(LoginRecord.user_id)).label('unique_users')
            ).filter(
                LoginRecord.login_time >= current_month_start,
                LoginRecord.login_time < current_month_end
            ).group_by(
                extract('day', LoginRecord.login_time)
            ).all()
            
            # 将查询结果填入统计字典
            for day_num, unique_users in daily_login_counts:
                if 1 <= day_num <= current_day:
                    login_stats[int(day_num)] = unique_users
            
            return jsonify({
                'labels': list(login_stats.keys()),
                'data': list(login_stats.values()),
                'total': sum(login_stats.values())
            })
            
        # 默认返回错误
        logging.error(f"无效的时间范围参数: {range_param}")
        return jsonify({'error': '无效的时间范围参数', 'valid_ranges': ['year', 'month']}), 400
    except ValueError as ve:
        logging.error(f"每日登录数据值错误: {str(ve)}")
        return jsonify({"error": "数据处理过程中出现错误"}), 422
    except TypeError as te:
        logging.error(f"每日登录数据类型错误: {str(te)}")
        return jsonify({"error": "数据类型错误"}), 422
    except Exception as e:
        logging.error(f"获取每日登录数据失败: {str(e)}")
        return jsonify({"error": "获取每日登录数据失败，请检查服务器日志"}), 500