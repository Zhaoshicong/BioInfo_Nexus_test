#!/bin/bash

# 维护任务脚本
# 用于执行数据库维护任务，包括清理未激活用户和优化数据库
# 建议通过crontab设置定时执行

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 设置日志文件
LOG_FILE="$SCRIPT_DIR/maintenance_tasks.log"

# 记录开始时间
echo "========================================" >> "$LOG_FILE"
echo "维护任务开始执行: $(date)" >> "$LOG_FILE"

# 1. 清理验证码已过期的未激活用户
echo "\n[任务1] 清理验证码已过期的未激活用户" >> "$LOG_FILE"
python3 "$SCRIPT_DIR/clean_inactive_users.py" --mode expired >> "$LOG_FILE" 2>&1

# 2. 清理长时间未激活的用户（超过30天）
echo "\n[任务2] 清理长时间未激活的用户" >> "$LOG_FILE"
python3 "$SCRIPT_DIR/clean_inactive_users.py" --mode old --days 30 >> "$LOG_FILE" 2>&1

# 3. 优化数据库（执行VACUUM操作）
echo "\n[任务3] 优化数据库" >> "$LOG_FILE"
python3 "$SCRIPT_DIR/vacuum_db.py" --analyze >> "$LOG_FILE" 2>&1

# 记录结束时间
echo "\n维护任务执行完成: $(date)" >> "$LOG_FILE"
echo "========================================\n" >> "$LOG_FILE"