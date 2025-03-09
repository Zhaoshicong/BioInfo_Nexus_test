# BioInfo Nexus 部署指南

本文档提供了将BioInfo Nexus部署到生产环境的详细步骤。

## 前提条件

- Python 3.7+
- pip (Python包管理器)
- 一个SMTP邮件服务器账号
- 域名（可选，但推荐）

## 安装步骤

### 1. 克隆代码库

```bash
git clone https://github.com/your-username/bioinfo-nexus.git
cd bioinfo-nexus
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制`.env.example`文件为`.env`，并根据您的环境进行配置：

```bash
cp .env.example .env
```

编辑`.env`文件，填写以下信息：

```bash
# 应用环境
FLASK_ENV=production

# 密钥（请生成一个强随机密钥）
SECRET_KEY=your_secret_key_here

# 邮件服务器配置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_email_password
MAIL_DEFAULT_SENDER=BioInfo Nexus <noreply@your-domain.com>

# 数据库配置
DATABASE_URI=sqlite:///instance/bioinfo_nexus.db
```

对于生产环境，建议使用更强大的数据库，如MySQL或PostgreSQL：

```
DATABASE_URI=mysql://username:password@localhost/bioinfo_nexus
```

或

```
DATABASE_URI=postgresql://username:password@localhost/bioinfo_nexus
```

### 4. 初始化数据库

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. 配置Web服务器

#### 使用Gunicorn（推荐）

安装Gunicorn：

```bash
pip install gunicorn
```

启动应用：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### 使用Nginx作为反向代理

安装Nginx：

```bash
# Ubuntu/Debian
sudo apt-get install nginx

# CentOS/RHEL
sudo yum install nginx
```

创建Nginx配置文件：

```
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6. 配置HTTPS（强烈推荐）

使用Let's Encrypt获取免费SSL证书：

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 7. 设置自动启动

创建systemd服务文件：

```
[Unit]
Description=BioInfo Nexus
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/bioinfo-nexus
ExecStart=/path/to/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl enable bioinfo-nexus
sudo systemctl start bioinfo-nexus
```

## 邮件服务器选项

### 1. 使用第三方邮件服务

#### SendGrid

1. 注册SendGrid账户
2. 获取API密钥
3. 配置`.env`文件：

```
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=your_sendgrid_api_key
```

#### 阿里云邮件推送

1. 注册阿里云账户并完成实名认证
2. 开通邮件推送服务：https://www.aliyun.com/product/directmail
3. 配置发信域名（需要您拥有一个域名）
   - 添加域名并完成DNS验证
4. 创建发信地址
   - 使用您验证过的域名
   - 设置发信人昵称（如"BioInfo Nexus"）
5. 创建SMTP密码
   - 在SMTP服务页面创建并保存密码
6. 配置`.env`文件：

```
# 使用HTTP端口
MAIL_SERVER=smtpdm.aliyun.com
MAIL_PORT=80
MAIL_USE_TLS=False
MAIL_USE_SSL=False
MAIL_USERNAME=noreply@your-domain.com  # 您创建的发信地址
MAIL_PASSWORD=your_smtp_password  # 您设置的SMTP密码
MAIL_DEFAULT_SENDER=BioInfo Nexus <noreply@your-domain.com>

# 或者使用SSL端口
# MAIL_SERVER=smtpdm.aliyun.com
# MAIL_PORT=465
# MAIL_USE_TLS=False
# MAIL_USE_SSL=True
# MAIL_USERNAME=noreply@your-domain.com
# MAIL_PASSWORD=your_smtp_password
# MAIL_DEFAULT_SENDER=BioInfo Nexus <noreply@your-domain.com>
```

7. 发信限制说明
   - 阿里云邮件推送对免费用户有每日发信量限制
   - 如需更高配额，可以升级为付费版本

### 2. 使用自己的邮件服务器

如果您有自己的域名，可以使用以下服务配置自己的邮件服务器：

- Google Workspace
- 腾讯企业邮箱
- 阿里企业邮箱

## 故障排除

### 邮件发送失败

1. 检查SMTP服务器配置是否正确
2. 确认邮箱账号和密码是否正确
3. 检查防火墙是否允许SMTP流量
4. 查看应用日志获取详细错误信息

### 数据库连接问题

1. 确认数据库服务是否运行
2. 检查数据库连接字符串是否正确
3. 确认数据库用户有足够的权限

## 安全建议

1. 定期更新系统和依赖包
2. 使用强密码和密钥
3. 启用HTTPS
4. 限制数据库访问
5. 配置防火墙
6. 定期备份数据

## 联系支持

如有任何问题，请联系：bioinfo.nexus@example.com 