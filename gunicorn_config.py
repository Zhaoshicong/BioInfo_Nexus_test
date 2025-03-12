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

# 工作进程数量 - 一般设置为 (2 * CPU核心数 + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# 每个工作进程的线程数
threads = 2

# 最大请求数，超过这个数量后工作进程会重启
max_requests = 2000
max_requests_jitter = 400

# 超时设置
timeout = 120
graceful_timeout = 120
keepalive = 5

# 日志设置
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# 进程名称
proc_name = "bioinfo_nexus"

# 预加载应用
preload_app = True

# 守护进程模式
daemon = False

# 确保日志目录存在
os.makedirs("logs", exist_ok=True) 