"""
使用SQLite直接查询数据库中的用户数量
这个脚本不依赖Flask，可以在任何目录运行
"""
import sqlite3
import os
import datetime

def count_users():
    """统计用户数量"""
    try:
        # 获取数据库路径 - 数据库位于instance目录中
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, 'bioinfo_nexus.db')
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            print(f"错误: 数据库文件不存在: {db_path}")
            return
        
        print(f"使用数据库: {db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 总用户数
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        print(f"总用户数: {total_users}")
        
        # 活跃用户数
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()[0]
        print(f"活跃用户数: {active_users}")
        
        # 今日注册用户数
        today = datetime.datetime.now().date()
        today_start = datetime.datetime.combine(today, datetime.time.min).isoformat()
        today_end = datetime.datetime.combine(today, datetime.time.max).isoformat()
        cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ? AND created_at <= ?", 
                      (today_start, today_end))
        today_users = cursor.fetchone()[0]
        print(f"今日注册用户数: {today_users}")
        
        # 本月注册用户数
        month_start = datetime.datetime(today.year, today.month, 1).isoformat()
        cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (month_start,))
        month_users = cursor.fetchone()[0]
        print(f"本月注册用户数: {month_users}")
        
        # 关闭连接
        conn.close()
        
    except Exception as e:
        print(f"查询数据库时出错: {str(e)}")

if __name__ == "__main__":
    count_users() 