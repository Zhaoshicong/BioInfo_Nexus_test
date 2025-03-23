from flask import Blueprint, jsonify
import sqlite3
from datetime import datetime, timedelta
import psutil
import os
import logging
from functools import wraps
import jwt
from flask import current_app, request

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

# 数据库连接函数
def get_db_connection():
    conn = sqlite3.connect('instance/bioinfo_nexus.db')
    conn.row_factory = sqlite3.Row
    return conn

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
            # 解码令牌
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            # 查询用户
            conn = get_db_connection()
            
            # 尝试使用users表查询
            user = conn.execute('SELECT * FROM users WHERE public_id = ?', (data['public_id'],)).fetchone()
            
            conn.close()
            
            if not user:
                return jsonify({"message": "用户未找到"}), 404
                
            if not user['is_admin']:
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
        conn = get_db_connection()
                
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
                new_count = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(created_at) = ?', 
                    (full_date,)
                ).fetchone()[0]
                new_users.append(int(new_count))  # 确保是整数
                
                # 活跃用户
                active_count = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(last_login) = ?', 
                    (full_date,)
                ).fetchone()[0]
                active_users.append(int(active_count))  # 确保是整数
                
                # 流失用户
                # 构建完整日期字符串用于计算
                current_year = datetime.now().year
                full_date = f"{current_year}-{date}"
                churn_date = (datetime.strptime(full_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
                churn_count = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(last_login) <= ? AND is_active = 1', 
                    (churn_date,)
                ).fetchone()[0]
                churn_users.append(int(churn_count))  # 确保是整数
            
            # 计算累计用户数
            total_users = []
            # 获取当前年份
            current_year = datetime.now().year
            # 获取第一个月之前的用户总数作为基数
            if labels:  # 确保labels不为空
                first_month_date = datetime(current_year, 1, 1)  # 使用当年1月1日作为基准
                running_total = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(created_at) < ?', 
                    (first_month_date.strftime('%Y-%m-%d'),)
                ).fetchone()[0]
                
                for i in range(len(new_users)):
                    # 累加新增用户，减去流失用户
                    running_total += new_users[i] - churn_users[i]
                    total_users.append(max(0, int(running_total)))  # 确保不会出现负数且为整数
            else:
                # 如果没有数据点，返回空列表
                total_users = []
                

                
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
                new_count = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(created_at) >= ? AND date(created_at) <= ?', 
                    (first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d'))
                ).fetchone()[0]
                new_users.append(int(new_count))  # 确保是整数
                
                # 活跃用户 - 整个月的统计
                active_count = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(last_login) >= ? AND date(last_login) <= ?', 
                    (first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d'))
                ).fetchone()[0]
                active_users.append(int(active_count))  # 确保是整数
                
                # 流失用户 - 使用上个月的最后一天作为基准日期
                # 对于1月，需要使用上一年的12月31日
                if month == 1:
                    churn_date = datetime(current_year - 1, 12, 31).strftime('%Y-%m-%d')
                else:
                    # 上个月的最后一天
                    churn_date = (first_day - timedelta(days=1)).strftime('%Y-%m-%d')
                
                churn_count = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(last_login) <= ? AND is_active = 1', 
                    (churn_date,)
                ).fetchone()[0]
                churn_users.append(int(churn_count))  # 确保是整数
            
            # 计算累计用户数
            total_users = []
            # 获取当前年份
            current_year = datetime.now().year
            # 获取第一个月之前的用户总数作为基数
            if labels:  # 确保labels不为空
                first_month_date = datetime(current_year, 1, 1)  # 使用当年1月1日作为基准
                running_total = conn.execute(
                    'SELECT COUNT(*) FROM users WHERE date(created_at) < ?', 
                    (first_month_date.strftime('%Y-%m-%d'),)
                ).fetchone()[0]
                
                for i in range(len(new_users)):
                    # 累加新增用户，减去流失用户
                    running_total += new_users[i] - churn_users[i]
                    total_users.append(max(0, int(running_total)))  # 确保不会出现负数且为整数
            else:
                # 如果没有数据点，返回空列表
                total_users = []
        
        conn.close()
        
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