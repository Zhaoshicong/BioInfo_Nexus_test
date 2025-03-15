#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
清理未激活用户脚本
用于清理数据库中未激活的用户和过期验证码记录
可以手动运行或设置为定时任务
"""

import os
import sys
import sqlite3
import datetime
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("user_cleanup.log"),
        logging.StreamHandler()
    ]
)

# 数据库路径
DB_PATH = 'instance/bioinfo_nexus.db'

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

def clean_expired_verification_codes(conn, dry_run=False):
    """清理验证码已过期的未激活用户"""
    try:
        # 获取当前时间
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # 查询验证码已过期的未激活用户
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, created_at FROM users WHERE is_active = 0 AND verification_code_expiry < ?", 
            (now,)
        )
        expired_users = cursor.fetchall()
        
        if not expired_users:
            logging.info("没有找到验证码已过期的未激活用户")
            return 0
        
        if dry_run:
            logging.info(f"找到 {len(expired_users)} 个验证码已过期的未激活用户:")
            for user in expired_users:
                logging.info(f"  - ID: {user['id']}, 邮箱: {user['email']}, 创建时间: {user['created_at']}")
            return len(expired_users)
        
        # 删除这些用户
        cursor.execute(
            "DELETE FROM users WHERE is_active = 0 AND verification_code_expiry < ?", 
            (now,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        
        logging.info(f"成功删除 {deleted_count} 个验证码已过期的未激活用户")
        return deleted_count
        
    except sqlite3.Error as e:
        logging.error(f"清理验证码过期用户时出错: {e}")
        conn.rollback()
        return 0

def clean_old_inactive_users(conn, days=30, dry_run=False):
    """清理长时间未激活的用户（超过指定天数）"""
    try:
        # 计算截止日期
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        # 查询长时间未激活的用户
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, created_at FROM users WHERE is_active = 0 AND created_at < ?", 
            (cutoff_date,)
        )
        old_users = cursor.fetchall()
        
        if not old_users:
            logging.info(f"没有找到超过 {days} 天未激活的用户")
            return 0
        
        if dry_run:
            logging.info(f"找到 {len(old_users)} 个超过 {days} 天未激活的用户:")
            for user in old_users:
                logging.info(f"  - ID: {user['id']}, 邮箱: {user['email']}, 创建时间: {user['created_at']}")
            return len(old_users)
        
        # 删除这些用户
        cursor.execute(
            "DELETE FROM users WHERE is_active = 0 AND created_at < ?", 
            (cutoff_date,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        
        logging.info(f"成功删除 {deleted_count} 个超过 {days} 天未激活的用户")
        return deleted_count
        
    except sqlite3.Error as e:
        logging.error(f"清理长时间未激活用户时出错: {e}")
        conn.rollback()
        return 0

def clean_all_inactive_users(conn, dry_run=False):
    """清理所有未激活的用户"""
    try:
        # 查询所有未激活的用户
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, created_at FROM users WHERE is_active = 0")
        inactive_users = cursor.fetchall()
        
        if not inactive_users:
            logging.info("没有找到未激活的用户")
            return 0
        
        if dry_run:
            logging.info(f"找到 {len(inactive_users)} 个未激活的用户:")
            for user in inactive_users:
                logging.info(f"  - ID: {user['id']}, 邮箱: {user['email']}, 创建时间: {user['created_at']}")
            return len(inactive_users)
        
        # 删除这些用户
        cursor.execute("DELETE FROM users WHERE is_active = 0")
        deleted_count = cursor.rowcount
        conn.commit()
        
        logging.info(f"成功删除所有 {deleted_count} 个未激活的用户")
        return deleted_count
        
    except sqlite3.Error as e:
        logging.error(f"清理所有未激活用户时出错: {e}")
        conn.rollback()
        return 0

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="清理未激活用户和过期验证码记录")
    parser.add_argument('--mode', choices=['expired', 'old', 'all'], default='expired',
                        help='清理模式: expired=清理验证码已过期的, old=清理长时间未激活的, all=清理所有未激活的')
    parser.add_argument('--days', type=int, default=30,
                        help='当选择old模式时，指定多少天前的未激活用户将被清理 (默认: 30)')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示将被删除的记录，不实际删除')
    args = parser.parse_args()
    
    # 检查数据库文件是否存在
    if not os.path.exists(DB_PATH):
        logging.error(f"数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    logging.info("开始清理未激活用户...")
    if args.dry_run:
        logging.info("【模拟运行模式】将显示要删除的记录但不会实际删除")
    
    # 连接数据库
    conn = get_db_connection()
    
    try:
        # 根据模式执行不同的清理操作
        if args.mode == 'expired':
            clean_expired_verification_codes(conn, args.dry_run)
        elif args.mode == 'old':
            clean_old_inactive_users(conn, args.days, args.dry_run)
        elif args.mode == 'all':
            clean_all_inactive_users(conn, args.dry_run)
        
        logging.info("清理操作完成")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main() 