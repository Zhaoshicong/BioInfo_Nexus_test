#!/bin/bash

# BioInfo Nexus VPS部署脚本
# 此脚本用于在VPS服务器上完整部署BioInfo Nexus应用

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
    echo -e "${BLUE}=================================================${NC}"
}

# 获取当前目录
CURRENT_DIR=$(pwd)
APP_NAME="bioinfo_nexus"
DOMAIN_NAME=""
SUBDOMAIN_NAME=""
USE_SUBDOMAIN=false

# 询问域名
read -p "请输入您的主域名 (如果没有，请直接按回车): " DOMAIN_INPUT
if [ ! -z "$DOMAIN_INPUT" ]; then
    DOMAIN_NAME=$DOMAIN_INPUT
    info "将使用主域名: $DOMAIN_NAME"
    
    # 询问是否使用二级域名
    read -p "是否需要设置二级域名? (y/n): " SUBDOMAIN_CHOICE
    if [[ "$SUBDOMAIN_CHOICE" == "y" || "$SUBDOMAIN_CHOICE" == "Y" ]]; then
        read -p "请输入二级域名前缀 (例如: bio，将生成 bio.$DOMAIN_NAME): " SUBDOMAIN_PREFIX
        if [ ! -z "$SUBDOMAIN_PREFIX" ]; then
            SUBDOMAIN_NAME="${SUBDOMAIN_PREFIX}.${DOMAIN_NAME}"
            USE_SUBDOMAIN=true
            info "将使用二级域名: $SUBDOMAIN_NAME"
        else
            warn "未提供二级域名前缀，将使用主域名: $DOMAIN_NAME"
        fi
    else
        info "将使用主域名: $DOMAIN_NAME"
    fi
else
    warn "未提供域名，将使用服务器IP地址"
fi

# 检测操作系统
section "检测操作系统"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    info "检测到操作系统: $OS"
else
    error "无法检测操作系统类型"
    exit 1
fi

# 更新系统
section "更新系统"
info "正在更新系统包..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    apt update && apt upgrade -y
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    yum update -y
else
    warn "未知的操作系统，跳过系统更新"
fi

# 安装必要软件
section "安装必要软件"
info "正在安装必要的软件包..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    apt install -y git python3 python3-pip python3-venv nginx supervisor certbot python3-certbot-nginx ufw
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    yum install -y git python3 python3-pip nginx supervisor certbot python3-certbot-nginx firewalld
else
    warn "未知的操作系统，请手动安装必要的软件包"
fi

# 检查Python和pip
section "检查Python环境"
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
pip install gunicorn

# 确保目录存在
section "创建必要的目录"
info "创建必要的目录..."
mkdir -p logs
mkdir -p temp
mkdir -p uploads/avatars
mkdir -p instance

# 检查配置文件
if [ ! -f ".env" ]; then
    warn "未找到.env文件，创建示例.env文件"
    cat > .env << EOF
# 应用配置
SECRET_KEY=your_secret_key_here
DEBUG=False
FLASK_ENV=production

# 邮件配置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_email_password
MAIL_DEFAULT_SENDER=your_email@example.com

# 数据库配置
DATABASE_URL=sqlite:///instance/database.db
EOF
    warn "请编辑.env文件，设置正确的环境变量"
fi

# 配置Gunicorn
section "配置Gunicorn"
info "创建Gunicorn配置文件..."
if [ ! -f "gunicorn_config.py" ]; then
    cat > gunicorn_config.py << EOF
# Gunicorn配置文件
import multiprocessing

# 绑定的IP和端口
bind = "0.0.0.0:8000"

# 工作进程数量
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时时间
timeout = 120

# 日志配置
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# 后台运行
daemon = False

# 进程ID文件
pidfile = "logs/gunicorn.pid"

# 重载
reload = False
EOF
fi

# 配置Supervisor
section "配置Supervisor"
info "创建Supervisor配置文件..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    SUPERVISOR_DIR="/etc/supervisor/conf.d"
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    SUPERVISOR_DIR="/etc/supervisord.d"
else
    SUPERVISOR_DIR="/etc/supervisor/conf.d"
fi

sudo mkdir -p $SUPERVISOR_DIR

sudo cat > "$SUPERVISOR_DIR/$APP_NAME.conf" << EOF
[program:$APP_NAME]
directory=$CURRENT_DIR
command=$CURRENT_DIR/venv/bin/gunicorn -c gunicorn_config.py wsgi:app
autostart=true
autorestart=true
stderr_logfile=$CURRENT_DIR/logs/supervisor_err.log
stdout_logfile=$CURRENT_DIR/logs/supervisor_out.log
user=root
environment=PATH="$CURRENT_DIR/venv/bin"
EOF

# 配置Nginx
section "配置Nginx"
info "创建Nginx配置文件..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    NGINX_DIR="/etc/nginx/sites-available"
    NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    NGINX_DIR="/etc/nginx/conf.d"
    NGINX_ENABLED_DIR=$NGINX_DIR
else
    NGINX_DIR="/etc/nginx/conf.d"
    NGINX_ENABLED_DIR=$NGINX_DIR
fi

sudo mkdir -p $NGINX_DIR

# 设置服务器名称
if $USE_SUBDOMAIN; then
    SERVER_NAME=$SUBDOMAIN_NAME
elif [ ! -z "$DOMAIN_NAME" ]; then
    SERVER_NAME=$DOMAIN_NAME
else
    SERVER_NAME='$host'
fi

sudo cat > "$NGINX_DIR/$APP_NAME.conf" << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $CURRENT_DIR/static/;
    }

    location /uploads/ {
        alias $CURRENT_DIR/uploads/;
    }

    location /temp/ {
        alias $CURRENT_DIR/temp/;
    }

    client_max_body_size 20M;
}
EOF

# 启用Nginx配置
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo ln -sf "$NGINX_DIR/$APP_NAME.conf" "$NGINX_ENABLED_DIR/$APP_NAME.conf"
fi

# 配置DNS记录提示
if $USE_SUBDOMAIN; then
    section "DNS配置提示"
    info "请确保在您的DNS服务商处添加以下DNS记录："
    info "类型: A 记录"
    info "主机名: $SUBDOMAIN_PREFIX"
    info "值: 您服务器的IP地址"
    info "TTL: 600 (或默认值)"
    echo ""
    info "或者添加以下CNAME记录："
    info "类型: CNAME 记录"
    info "主机名: $SUBDOMAIN_PREFIX"
    info "值: $DOMAIN_NAME"
    info "TTL: 600 (或默认值)"
    echo ""
    read -p "按回车键继续..." CONTINUE
fi

# 配置SSL证书
if [ ! -z "$DOMAIN_NAME" ]; then
    section "配置SSL证书"
    if $USE_SUBDOMAIN; then
        info "正在为二级域名 $SUBDOMAIN_NAME 配置SSL证书..."
        sudo certbot --nginx -d $SUBDOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
    else
        info "正在为域名 $DOMAIN_NAME 配置SSL证书..."
        sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
    fi
fi

# 配置防火墙
section "配置防火墙"
info "配置防火墙规则..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo ufw allow ssh
    sudo ufw allow http
    sudo ufw allow https
    
    # 检查防火墙状态，如果未启用则启用
    if ! sudo ufw status | grep -q "Status: active"; then
        info "启用UFW防火墙..."
        sudo ufw --force enable
    fi
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo systemctl start firewalld
    sudo systemctl enable firewalld
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
fi

# 重启服务
section "重启服务"
info "重启Supervisor..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo systemctl restart supervisor
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo systemctl restart supervisord
fi

info "重启Nginx..."
sudo systemctl restart nginx

# 设置自动启动
section "设置自动启动"
info "设置服务自动启动..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo systemctl enable supervisor
    sudo systemctl enable nginx
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo systemctl enable supervisord
    sudo systemctl enable nginx
fi

# 创建备份脚本
section "创建备份脚本"
info "创建数据库备份脚本..."
cat > backup.sh << EOF
#!/bin/bash
# 数据库备份脚本

# 创建备份目录
mkdir -p backups

# 备份数据库
cp instance/database.db backups/database_\$(date +%Y%m%d).db

# 删除30天前的备份
find backups -name "database_*.db" -type f -mtime +30 -delete

echo "数据库备份完成: backups/database_\$(date +%Y%m%d).db"
EOF

chmod +x backup.sh

# 添加定时任务
info "添加每日备份定时任务..."
(crontab -l 2>/dev/null; echo "0 2 * * * $CURRENT_DIR/backup.sh") | crontab -

# 部署完成
section "部署完成"
info "BioInfo Nexus已成功部署到VPS服务器！"
info "您可以通过以下地址访问您的应用："

if $USE_SUBDOMAIN; then
    info "http://$SUBDOMAIN_NAME"
    info "https://$SUBDOMAIN_NAME (如果SSL配置成功)"
elif [ ! -z "$DOMAIN_NAME" ]; then
    info "http://$DOMAIN_NAME"
    info "https://$DOMAIN_NAME (如果SSL配置成功)"
else
    # 获取服务器IP地址
    SERVER_IP=$(hostname -I | awk '{print $1}')
    info "http://$SERVER_IP"
fi

info "如需查看应用日志，请运行："
info "tail -f $CURRENT_DIR/logs/supervisor_out.log"

info "如需重启应用，请运行："
info "sudo supervisorctl restart $APP_NAME"

info "感谢使用BioInfo Nexus！" 