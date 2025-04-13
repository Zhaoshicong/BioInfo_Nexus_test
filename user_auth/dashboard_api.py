from flask import Blueprint, jsonify
# import sqlite3  # 移除 sqlite3 导入
from datetime import datetime, timedelta
import psutil
import os
import logging
from functools import wraps
import jwt
from flask import current_app, request
from .user_system import db, User  # 添加 SQLAlchemy 导入

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

# 数据库连接函数 - 已不再需要
# def get_db_connection():
#    conn = sqlite3.connect('instance/bioinfo_nexus.db')
#    conn.row_factory = sqlite3.Row
#    return conn

# 管理员权限检查装饰器
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 从请求头获取令牌
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "缺少认证令牌"}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # 解码令牌 - 使用与auth_routes.py相同的密钥获取逻辑
            # 获取密钥，确保与登录时使用的相同
            secret_key = current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY', 'dev_key_please_change')
            if not isinstance(secret_key, str):
                secret_key = str(secret_key)  # 转换为字符串
            
            # 解码令牌
            data = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # 使用 SQLAlchemy 查询用户
            user = User.query.filter_by(public_id=data['public_id']).first()
            
            if not user:
                return jsonify({"message": "用户未找到"}), 404
                
            if not user.is_admin:
                return jsonify({"message": "需要管理员权限"}), 403
                
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "令牌已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "无效的令牌"}), 401
        except Exception as e:
            return jsonify({"message": f"认证错误: {str(e)}"}), 401
            
    return decorated

# 获取系统资源使用情况
@dashboard_bp.route('/resource-usage', methods=['GET'])
@admin_required
def get_resource_usage():
    try:
        # 获取CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 获取内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 获取磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # 获取网络使用率（这里使用一个估算值，实际应根据网络带宽计算）
        # 由于网络使用率需要监控一段时间的流量，这里使用一个模拟值
        # 在实际应用中，可以通过监控网络接口的字节发送/接收量来计算
        network_percent = min(psutil.net_io_counters().bytes_sent % 100, 100)
        
        return jsonify({
            'cpu': round(cpu_percent, 2),
            'memory': round(memory_percent, 2),
            'disk': round(disk_percent, 2),
            'network': round(network_percent, 2)
        })
    except Exception as e:
        logging.error(f"获取系统资源使用情况失败: {str(e)}")
        return jsonify({"error": f"获取系统资源使用情况失败: {str(e)}"}), 500

# 获取用户增长数据
@dashboard_bp.route('/user-growth', methods=['GET'])
@admin_required
def get_user_growth():
    try:
        time_range = request.args.get('range', 'year')  # 默认为年度数据
        # conn = get_db_connection()
                
        if time_range == 'month':
            # 获取当前自然月的数据
            today = datetime.now().date()
            # 计算本月的第一天
            start_of_month = today.replace(day=1)
            # 计算下个月的第一天
            if start_of_month.month == 12:
                next_month = datetime(start_of_month.year + 1, 1, 1).date()
            else:
                next_month = datetime(start_of_month.year, start_of_month.month + 1, 1).date()
            # 计算本月的最后一天
            end_of_month = next_month - timedelta(days=1)
            
            labels = []
            new_users = []
            active_users = []
            churn_users = []
            
            # 生成本月每一天的日期（只显示到当前日期）
            days_in_month = (end_of_month - start_of_month).days + 1
            for i in range(days_in_month):
                current_date = start_of_month + timedelta(days=i)
                # 检查是否超过当前日期
                if current_date > today:
                    break
                    
                date = current_date.strftime('%m-%d')  # 移除年份显示，只保留月和日
                labels.append(date)
                
                # 新增用户
                # 构建完整日期字符串用于查询
                current_year = datetime.now().year
                full_date = f"{current_year}-{date}"
                new_count = User.query.filter(User.created_at.like(f"{current_year}-{date}")).count()
                new_users.append(int(new_count))  # 确保是整数
                
                # 活跃用户
                active_count = User.query.filter(User.last_login.like(f"{current_year}-{date}")).count()
                active_users.append(int(active_count))  # 确保是整数
                
                # 流失用户
                # 构建完整日期字符串用于计算
                current_year = datetime.now().year
                full_date = f"{current_year}-{date}"
                churn_date = (datetime.strptime(full_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
                churn_count = User.query.filter(User.last_login <= churn_date, User.is_active == 1).count()
                churn_users.append(int(churn_count))  # 确保是整数
            
            # 计算累计用户数 - 使用方法二：时间点快照
            total_users = []
            if labels: # 确保有日期标签
                for i in range(len(labels)):
                    # 获取当前循环对应的日期对象 (注意：labels 格式是 '%m-%d')
                    # 需要结合年份来构建完整的日期
                    current_date_str = f"{today.year}-{labels[i]}"
                    try:
                        # 确定该时间点（当天结束时）
                        end_of_day_dt = datetime.strptime(current_date_str, '%Y-%m-%d')
                        # 查询截止到该日期（包含当天）的用户总数
                        snapshot_total = User.query.filter(User.created_at <= end_of_day_dt.strftime('%Y-%m-%d')).count()
                        total_users.append(int(snapshot_total)) # 添加该时间点的总数
                    except ValueError:
                        # 如果日期解析失败（理论上不应发生），添加0或上一个值
                        total_users.append(total_users[-1] if total_users else 0)
            
        else:  # year
            # 获取当前自然年的1月到12月数据（按月统计）
            current_year = datetime.now().year
            current_month = datetime.now().month  # 获取当前月份
            labels = []
            new_users = []
            active_users = []
            churn_users = []
            
            # 只处理到当前月份的数据
            for month in range(1, current_month + 1):
                # 计算月份的第一天和最后一天
                first_day = datetime(current_year, month, 1)
                
                # 计算月份的最后一天
                if month == 12:
                    last_day = datetime(current_year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = datetime(current_year, month + 1, 1) - timedelta(days=1)
                
                # 如果是当前月份，只统计到当前日期
                if month == datetime.now().month:
                    last_day = datetime.now().date()
                
                # 使用中文月份名称作为标签，不添加年份
                month_label = f"{month}月"
                labels.append(month_label)
                
                # 新增用户 - 整个月的统计
                new_count = User.query.filter(User.created_at >= first_day.strftime('%Y-%m-%d'), User.created_at <= last_day.strftime('%Y-%m-%d')).count()
                new_users.append(int(new_count))  # 确保是整数
                
                # 活跃用户 - 整个月的统计
                active_count = User.query.filter(User.last_login >= first_day.strftime('%Y-%m-%d'), User.last_login <= last_day.strftime('%Y-%m-%d')).count()
                active_users.append(int(active_count))  # 确保是整数
                
                # 流失用户 - 使用上个月的最后一天作为基准日期
                # 对于1月，需要使用上一年的12月31日
                if month == 1:
                    churn_date = datetime(current_year - 1, 12, 31).strftime('%Y-%m-%d')
                else:
                    # 上个月的最后一天
                    churn_date = (first_day - timedelta(days=1)).strftime('%Y-%m-%d')
                
                churn_count = User.query.filter(User.last_login <= churn_date, User.is_active == 1).count()
                churn_users.append(int(churn_count))  # 确保是整数
            
            # 计算累计用户数 - 使用方法二：时间点快照
            total_users = []
            if labels: # 确保有月份标签
                for i in range(len(labels)):
                    # 获取当前循环对应的月份 (数字)
                    month = i + 1 
                    # 确定该时间点（当月最后一天结束时）
                    if month == 12:
                        end_of_month_dt = datetime(current_year, 12, 31) 
                    else:
                        # 下个月的第一天再减一天
                        end_of_month_dt = datetime(current_year, month + 1, 1) - timedelta(days=1)
                    
                    # 如果是当前月份，并且还没到月底，用当前日期作为结束点
                    if month == current_month and datetime.now().date() < end_of_month_dt.date():
                         end_of_period_dt = datetime.now()
                    else:
                         end_of_period_dt = end_of_month_dt
                    
                    # 查询截止到该时间点（包含当天）的用户总数
                    snapshot_total = User.query.filter(User.created_at <= end_of_period_dt.strftime('%Y-%m-%d %H:%M:%S')).count()
                    total_users.append(int(snapshot_total)) # 添加该时间点的总数
        
        # conn.close()
        
        return jsonify({
            'labels': labels,
            'new_users': new_users,
            'total_users': total_users,
            'active_users': active_users,
            'churn_users': churn_users
        })
    except Exception as e:
        logging.error(f"获取用户增长数据失败: {str(e)}")
        return jsonify({"error": f"获取用户增长数据失败: {str(e)}"}), 500