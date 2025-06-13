#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试AI使用限制的脚本
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from user_auth.user_system import db, User, AIUsageRecord

def quick_test(username, action="check"):
    """
    快速测试函数
    
    Args:
        username (str): 用户名
        action (str): 操作类型 - check, consume25, consume100, clear
    """
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return
        
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if action == "check":
            # 查看当前状态
            current_usage = AIUsageRecord.query.filter(
                AIUsageRecord.user_id == user.id,
                AIUsageRecord.usage_date >= current_month_start
            ).count()
            
            usage_limits = {'free': 25, 'plus': 100, 'premium': -1}
            user_limit = usage_limits.get(user.membership_level, 25)
            
            print(f"👤 用户: {username}")
            print(f"🎫 会员等级: {user.membership_level}")
            print(f"📊 当前使用: {current_usage}")
            print(f"🔢 月度限制: {'无限制' if user_limit == -1 else user_limit}")
            
            if user_limit > 0:
                remaining = user_limit - current_usage
                percentage = (current_usage / user_limit * 100)
                print(f"⏳ 剩余次数: {remaining}")
                print(f"📈 使用百分比: {percentage:.1f}%")
                
                if current_usage >= user_limit:
                    print("🚫 已达到使用限制！")
                elif percentage >= 90:
                    print("⚠️  接近使用限制！")
        
        elif action == "consume25":
            # 消耗25次（普通用户达到限制）
            for i in range(25):
                record = AIUsageRecord(user_id=user.id, tool_name="快速测试", sequence_length=100)
                db.session.add(record)
            db.session.commit()
            print(f"✅ 已为 {username} 添加25次使用记录")
            quick_test(username, "check")
        
        elif action == "consume100":
            # 消耗100次（Plus用户达到限制）
            for i in range(100):
                record = AIUsageRecord(user_id=user.id, tool_name="快速测试", sequence_length=100)
                db.session.add(record)
            db.session.commit()
            print(f"✅ 已为 {username} 添加100次使用记录")
            quick_test(username, "check")
        
        elif action == "clear":
            # 清空使用记录
            deleted_count = AIUsageRecord.query.filter(
                AIUsageRecord.user_id == user.id,
                AIUsageRecord.usage_date >= current_month_start
            ).delete()
            db.session.commit()
            print(f"🗑️  已清空 {username} 的 {deleted_count} 条使用记录")
            quick_test(username, "check")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python quick_test_ai_limit.py <用户名> [操作]")
        print("")
        print("操作选项:")
        print("  check      - 查看使用情况（默认）")
        print("  consume25  - 消耗25次（普通用户达限）")
        print("  consume100 - 消耗100次（Plus用户达限）")
        print("  clear      - 清空使用记录")
        print("")
        print("示例:")
        print("  python quick_test_ai_limit.py testuser")
        print("  python quick_test_ai_limit.py testuser consume25")
        print("  python quick_test_ai_limit.py testuser clear")
        sys.exit(1)
    
    username = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "check"
    
    quick_test(username, action) 