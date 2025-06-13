#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI使用次数消耗测试脚本
用于测试AI使用限制功能
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from user_auth.user_system import db, User, AIUsageRecord

def consume_ai_usage(username, count=1, tool_name="测试工具"):
    """
    为指定用户消耗AI使用次数
    
    Args:
        username (str): 用户名
        count (int): 要消耗的次数
        tool_name (str): 工具名称
    """
    with app.app_context():
        # 查找用户
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return False
        
        print(f"📊 用户信息:")
        print(f"   用户名: {user.username}")
        print(f"   会员等级: {user.membership_level}")
        print(f"   是否管理员: {user.is_admin}")
        
        # 获取当前使用次数
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_usage = AIUsageRecord.query.filter(
            AIUsageRecord.user_id == user.id,
            AIUsageRecord.usage_date >= current_month_start
        ).count()
        
        print(f"   当前月使用次数: {current_usage}")
        
        # 添加使用记录
        try:
            for i in range(count):
                usage_record = AIUsageRecord(
                    user_id=user.id,
                    tool_name=tool_name,
                    sequence_length=100  # 模拟序列长度
                )
                db.session.add(usage_record)
            
            db.session.commit()
            
            # 重新查询使用次数
            new_usage = AIUsageRecord.query.filter(
                AIUsageRecord.user_id == user.id,
                AIUsageRecord.usage_date >= current_month_start
            ).count()
            
            print(f"✅ 成功添加 {count} 次使用记录")
            print(f"   更新后使用次数: {new_usage}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 添加使用记录失败: {str(e)}")
            return False

def check_ai_usage(username):
    """
    检查指定用户的AI使用情况
    
    Args:
        username (str): 用户名
    """
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return
        
        # 获取当前使用次数
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_usage = AIUsageRecord.query.filter(
            AIUsageRecord.user_id == user.id,
            AIUsageRecord.usage_date >= current_month_start
        ).count()
        
        # 获取限制次数
        usage_limits = {
            'free': 25,
            'plus': 100,
            'premium': -1  # -1表示无限制
        }
        
        user_limit = usage_limits.get(user.membership_level, 25)
        remaining = user_limit - current_usage if user_limit > 0 else -1
        usage_percentage = (current_usage / user_limit * 100) if user_limit > 0 else 0
        
        print(f"📊 {username} 的AI使用情况:")
        print(f"   会员等级: {user.membership_level}")
        print(f"   当前使用: {current_usage}")
        print(f"   月度限制: {'无限制' if user_limit == -1 else user_limit}")
        print(f"   剩余次数: {'无限制' if remaining == -1 else remaining}")
        print(f"   使用百分比: {usage_percentage:.1f}%")
        
        if user_limit > 0 and current_usage >= user_limit:
            print("⚠️  已达到使用限制！")
        elif user_limit > 0 and usage_percentage >= 90:
            print("⚠️  接近使用限制！")

def clear_ai_usage(username):
    """
    清空指定用户的AI使用记录
    
    Args:
        username (str): 用户名
    """
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return False
        
        try:
            # 删除当月的使用记录
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            deleted_count = AIUsageRecord.query.filter(
                AIUsageRecord.user_id == user.id,
                AIUsageRecord.usage_date >= current_month_start
            ).delete()
            
            db.session.commit()
            print(f"✅ 已清空 {username} 的 {deleted_count} 条AI使用记录")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 清空使用记录失败: {str(e)}")
            return False

def main():
    """主函数"""
    print("🧪 AI使用次数测试工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 查看用户AI使用情况")
        print("2. 消耗AI使用次数")
        print("3. 批量消耗次数（快速测试）")
        print("4. 清空AI使用记录")
        print("5. 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == '1':
            username = input("请输入用户名: ").strip()
            if username:
                check_ai_usage(username)
        
        elif choice == '2':
            username = input("请输入用户名: ").strip()
            if username:
                try:
                    count = int(input("请输入要消耗的次数 (默认1): ").strip() or "1")
                    tool_name = input("请输入工具名称 (默认'测试工具'): ").strip() or "测试工具"
                    consume_ai_usage(username, count, tool_name)
                except ValueError:
                    print("❌ 请输入有效的数字")
        
        elif choice == '3':
            username = input("请输入用户名: ").strip()
            if username:
                print("\n快速测试选项:")
                print("1. 消耗到90%限制 (普通用户22次, Plus用户90次)")
                print("2. 消耗到100%限制 (普通用户25次, Plus用户100次)")
                print("3. 超出限制 (普通用户30次, Plus用户110次)")
                
                test_choice = input("请选择测试类型 (1-3): ").strip()
                
                with app.app_context():
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        print(f"❌ 用户 '{username}' 不存在")
                        continue
                    
                    # 先清空现有记录
                    clear_ai_usage(username)
                    
                    # 根据选择消耗次数
                    if test_choice == '1':
                        if user.membership_level == 'plus':
                            consume_ai_usage(username, 90, "批量测试-90%")
                        else:
                            consume_ai_usage(username, 22, "批量测试-90%")
                    elif test_choice == '2':
                        if user.membership_level == 'plus':
                            consume_ai_usage(username, 100, "批量测试-100%")
                        else:
                            consume_ai_usage(username, 25, "批量测试-100%")
                    elif test_choice == '3':
                        if user.membership_level == 'plus':
                            consume_ai_usage(username, 110, "批量测试-超限")
                        else:
                            consume_ai_usage(username, 30, "批量测试-超限")
                    
                    # 显示结果
                    check_ai_usage(username)
        
        elif choice == '4':
            username = input("请输入用户名: ").strip()
            if username:
                confirm = input(f"确定要清空 {username} 的AI使用记录吗? (y/N): ").strip().lower()
                if confirm == 'y':
                    clear_ai_usage(username)
        
        elif choice == '5':
            print("👋 再见!")
            break
        
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == '__main__':
    main() 