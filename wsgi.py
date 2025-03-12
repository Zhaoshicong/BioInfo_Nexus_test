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
    application.run() 