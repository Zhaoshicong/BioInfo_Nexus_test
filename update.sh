#!/bin/bash
# BioInfo Nexus 更新脚本

# 确保脚本中断时停止执行
set -e

# 输出彩色文本
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

section() {
    echo -e "\n${BLUE}[SECTION] $1${NC}"
    echo -e "${BLUE}==================================================${NC}"
}

# 获取当前目录
CURRENT_DIR=$(pwd)
APP_NAME="bioinfo_nexus"

# 备份重要数据
section "备份重要数据"
BACKUP_DIR="backups/update_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 备份数据库
info "备份数据库..."
if [ -d "instance" ]; then
    mkdir -p $BACKUP_DIR/instance
    if [ -f "instance/database.db" ]; then
        cp instance/database.db $BACKUP_DIR/instance/
        info "数据库已备份到 $BACKUP_DIR/instance/database.db"
    else
        warn "未找到数据库文件 instance/database.db"
    fi
fi

# 备份用户上传的文件
info "备份用户上传的文件..."
if [ -d "uploads" ]; then
    mkdir -p $BACKUP_DIR/uploads
    cp -r uploads/* $BACKUP_DIR/uploads/ 2>/dev/null || true
    info "用户上传文件已备份到 $BACKUP_DIR/uploads/"
fi

# 备份临时文件
if [ -d "temp" ]; then
    mkdir -p $BACKUP_DIR/temp
    cp -r temp/* $BACKUP_DIR/temp/ 2>/dev/null || true
    info "临时文件已备份到 $BACKUP_DIR/temp/"
fi

# 备份环境配置
if [ -f ".env" ]; then
    cp .env $BACKUP_DIR/
    info "环境配置已备份到 $BACKUP_DIR/.env"
fi

# 备份代码文件
info "备份关键代码文件..."
cp -r *.py *.sh requirements.txt $BACKUP_DIR/ 2>/dev/null || true

# 检查是否是Git仓库
if [ ! -d ".git" ]; then
    error "当前目录不是Git仓库，无法使用git pull更新"
    exit 1
fi

# 保存当前分支名称
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")
info "当前分支: $CURRENT_BRANCH"

# 检查是否有未提交的更改
if ! git diff --quiet || ! git diff --cached --quiet; then
    warn "检测到本地有未提交的更改"
    read -p "是否继续更新？这可能会导致本地更改被覆盖 (y/n): " CONTINUE
    if [[ "$CONTINUE" != "y" && "$CONTINUE" != "Y" ]]; then
        info "更新已取消"
        exit 0
    fi
    
    # 创建本地更改的补丁
    info "创建本地更改的补丁..."
    git diff > $BACKUP_DIR/local_changes.patch
    info "本地更改已保存到 $BACKUP_DIR/local_changes.patch"
fi

# 拉取最新代码
section "拉取最新代码"
info "正在从GitHub拉取最新代码..."
git fetch origin

# 显示将要更新的内容
info "以下是将要更新的内容:"
git log --oneline HEAD..origin/$CURRENT_BRANCH

# 确认更新
read -p "确认更新？(y/n): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    info "更新已取消"
    exit 0
fi

# 执行更新
git pull origin $CURRENT_BRANCH

# 恢复重要数据
section "恢复重要数据"

# 恢复数据库（如果不存在）
if [ ! -f "instance/database.db" ] && [ -f "$BACKUP_DIR/instance/database.db" ]; then
    info "恢复数据库..."
    mkdir -p instance
    cp $BACKUP_DIR/instance/database.db instance/
fi

# 恢复用户上传的文件
info "确保用户上传的文件不被覆盖..."
if [ -d "$BACKUP_DIR/uploads" ]; then
    mkdir -p uploads
    cp -rn $BACKUP_DIR/uploads/* uploads/ 2>/dev/null || true
fi

# 恢复环境配置
if [ ! -f ".env" ] && [ -f "$BACKUP_DIR/.env" ]; then
    info "恢复环境配置..."
    cp $BACKUP_DIR/.env .
fi

# 激活虚拟环境
section "更新环境"
if [ -d "venv" ]; then
    info "激活虚拟环境..."
    source venv/bin/activate
else
    info "创建新的虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
fi

# 安装依赖
info "更新依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 检查数据库迁移
section "检查数据库"
info "检查是否需要数据库迁移..."
if [ -f "migrations/migrate.py" ]; then
    info "执行数据库迁移..."
    python migrations/migrate.py
else
    info "未找到迁移脚本，跳过数据库迁移"
fi

# 确保目录权限正确
section "设置权限"
info "确保目录权限正确..."
chmod -R 755 uploads temp logs 2>/dev/null || true

# 重启应用
section "重启服务"
info "重启应用..."
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl restart $APP_NAME
else
    warn "未找到supervisorctl，请手动重启应用"
fi

# 检查Nginx配置
if [ -f "nginx_bioinfo.conf" ]; then
    if command -v nginx &> /dev/null; then
        NGINX_CONF_DIR="/etc/nginx/conf.d"
        if [ -d "/etc/nginx/sites-available" ]; then
            NGINX_CONF_DIR="/etc/nginx/sites-available"
        fi
        
        if [ -f "$NGINX_CONF_DIR/$APP_NAME.conf" ]; then
            CURRENT_NGINX_HASH=$(md5sum nginx_bioinfo.conf | awk '{print $1}')
            INSTALLED_NGINX_HASH=$(md5sum $NGINX_CONF_DIR/$APP_NAME.conf 2>/dev/null | awk '{print $1}' || echo "")
            
            if [ "$CURRENT_NGINX_HASH" != "$INSTALLED_NGINX_HASH" ]; then
                section "更新Nginx配置"
                info "检测到Nginx配置变更，正在更新..."
                sudo cp nginx_bioinfo.conf $NGINX_CONF_DIR/$APP_NAME.conf
                sudo systemctl restart nginx
            fi
        fi
    fi
fi

# 更新完成
section "更新完成"
info "BioInfo Nexus已成功更新！"
info "数据库和用户上传的文件已保留"
info "如需查看应用日志，请运行："
info "tail -f $CURRENT_DIR/logs/supervisor_out.log"

# 显示备份信息
info "所有更新前的备份保存在: $BACKUP_DIR"
info "如果更新后出现问题，可以使用这些备份恢复" 