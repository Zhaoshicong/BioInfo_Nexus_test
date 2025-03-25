#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库优化脚本
用于对SQLite数据库执行VACUUM操作，整理碎片和回收未使用的空间
可以手动运行或设置为定时任务
"""

import os
import sys
import sqlite3
import datetime
import argparse
import logging
import time

# 配置日志 - 只使用标准输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bioinfo_nexus.db')

def get_db_connection():
    """建立数据库连接"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"连接数据库失败: {e}")
        if conn:
            conn.close()
        sys.exit(1)

def get_db_size():
    """获取数据库文件大小"""
    try:
        size_bytes = os.path.getsize(DB_PATH)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb
    except OSError as e:
        logging.error(f"获取数据库大小失败: {e}")
        return 0

def vacuum_database(conn, analyze=False, dry_run=False):
    """执行VACUUM操作优化数据库"""
    try:
        # 记录操作开始时间
        start_time = time.time()
        
        # 记录操作前数据库大小
        before_size = get_db_size()
        logging.info(f"VACUUM操作前数据库大小: {before_size:.2f} MB")
        
        if dry_run:
            logging.info("【模拟运行模式】将显示VACUUM操作信息但不会实际执行")
            return True
        
        # 执行VACUUM操作
        cursor = conn.cursor()
        logging.info("开始执行VACUUM操作...")
        cursor.execute("VACUUM")
        
        # 如果需要，执行ANALYZE操作
        if analyze:
            logging.info("开始执行ANALYZE操作...")
            cursor.execute("ANALYZE")
        
        # 记录操作后数据库大小
        after_size = get_db_size()
        logging.info(f"VACUUM操作后数据库大小: {after_size:.2f} MB")
        
        # 计算节省的空间
        saved_space = before_size - after_size
        if saved_space > 0:
            logging.info(f"优化节省了 {saved_space:.2f} MB 空间 ({(saved_space/before_size)*100:.2f}%)")
        else:
            logging.info("数据库已经处于最佳状态，没有空间被释放")
        
        # 记录操作耗时
        elapsed_time = time.time() - start_time
        logging.info(f"VACUUM操作完成，耗时: {elapsed_time:.2f} 秒")
        
        return True
        
    except sqlite3.Error as e:
        logging.error(f"执行VACUUM操作时出错: {e}")
        return False

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="对SQLite数据库执行VACUUM操作，整理碎片和回收未使用的空间")
    parser.add_argument('--analyze', action='store_true',
                        help='在VACUUM后执行ANALYZE操作，更新统计信息以优化查询计划')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示将执行的操作，不实际执行')
    args = parser.parse_args()
    
    # 检查数据库文件是否存在
    if not os.path.exists(DB_PATH):
        logging.error(f"数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    logging.info("开始数据库优化操作...")
    
    # 连接数据库
    conn = get_db_connection()
    
    try:
        # 执行VACUUM操作
        success = vacuum_database(conn, args.analyze, args.dry_run)
        
        if success:
            logging.info("数据库优化操作完成")
        else:
            logging.error("数据库优化操作失败")
            sys.exit(1)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
'''
python vacuum_db.py  # 基本执行
python vacuum_db.py --analyze  # 执行VACUUM和ANALYZE
python vacuum_db.py --dry-run  # 模拟运行
唯一要注意的是，在Linux系统中您可能需要先给脚本添加执行权限
chmod +x vacuum_db.py
之后也可以直接使用 ./vacuum_db.py 来执行脚本。
'''