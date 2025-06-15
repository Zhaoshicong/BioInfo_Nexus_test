#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gunicorn配置文件 - BioInfo Nexus
"""

import multiprocessing
import os

# 绑定的IP和端口
bind = "0.0.0.0:8000"

# 工作模式
worker_class = "gevent"

# 工作进程数量 - 针对4核4GB服务器优化
workers = 4

# 每个工作进程的线程数
threads = 4

# 最大请求数，超过这个数量后工作进程会重启
max_requests = 1000
max_requests_jitter = 200

# 超时设置
timeout = 60
graceful_timeout = 60
keepalive = 10

# 工作进程连接数限制
worker_connections = 1000

# 确保日志目录存在
log_dir = "/www/wwwroot/default/BioInfo_Nexus_test/logs"
try:
    os.makedirs(log_dir, exist_ok=True)
    print(f"日志目录已创建: {log_dir}")
except Exception as e:
    print(f"创建日志目录失败: {e}")
    # 如果无法创建logs目录，使用系统临时目录
    log_dir = "/tmp/bioinfo_nexus_logs"
    os.makedirs(log_dir, exist_ok=True)
    print(f"使用备用日志目录: {log_dir}")

# 日志设置
accesslog = f"{log_dir}/gunicorn_access.log"
errorlog = f"{log_dir}/gunicorn_error.log"
loglevel = "info"

# 进程名称
proc_name = "bioinfo_nexus"

# 预加载应用
preload_app = True

# 守护进程模式
daemon = False
# 确保日志目录存在
os.makedirs("logs", exist_ok=True)
