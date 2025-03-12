#!/bin/bash

# BioInfo Nexus 部署脚本
# 此脚本用于在生产环境中部署应用

# 确保脚本中断时停止执行
set -e

# 输出彩色文本
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 输出带颜色的信息
info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# 检查Python和pip
info "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    error "未找到Python3，请安装Python 3.8或更高版本"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    error "未找到pip3，请安装pip"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    info "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
info "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
info "安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 确保目录存在
info "创建必要的目录..."
mkdir -p logs
mkdir -p temp
mkdir -p uploads/avatars
mkdir -p instance

# 检查配置文件
if [ ! -f ".env" ]; then
    warn "未找到.env文件，请确保已正确配置环境变量"
fi

# 启动应用
info "使用Gunicorn启动应用..."
if command -v supervisorctl &> /dev/null; then
    # 使用supervisor重启应用
    info "使用supervisor重启应用..."
    supervisorctl restart bioinfo_nexus
else
    # 直接启动Gunicorn
    info "直接启动Gunicorn..."
    gunicorn -c gunicorn_config.py wsgi:application
fi

info "部署完成！" 