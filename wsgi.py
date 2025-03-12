#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WSGI配置文件 - BioInfo Nexus
此文件作为WSGI服务器(如Gunicorn)的入口点
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 确保应用目录在Python路径中
sys.path.insert(0, os.path.dirname(__file__))

# 导入Flask应用
from app import app as application

# 确保目录存在
for directory in ['temp', 'uploads/avatars', 'instance']:
    os.makedirs(directory, exist_ok=True)

if __name__ == "__main__":
    # 显示局域网IP地址
    import socket
    def get_local_ip():
        try:
            # 创建一个临时socket连接，获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'
    
    local_ip = get_local_ip()
    #print(f"\n* 局域网访问地址: http://{local_ip}:5000")
    #print(f"* 本地访问地址: http://localhost:5000\n")
    
    # 直接运行时使用开发服务器
    application.run(host='0.0.0.0', port=5000, debug=True)