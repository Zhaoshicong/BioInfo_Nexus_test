# BioInfo Nexus 部署指南

本文档详细说明如何在生产环境中部署BioInfo Nexus应用。

## 系统要求

- Python 3.8或更高版本
- Nginx服务器（用于静态文件和反向代理）
- 足够的服务器资源（至少1GB内存）
- Linux、Windows或macOS操作系统

## 部署步骤

### 1. 准备项目

1. 下载或克隆项目代码:
   ```bash
   git clone https://github.com/yourusername/BioInfo-Nexus.git
   cd BioInfo-Nexus
   ```

2. 创建并激活Python虚拟环境:
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. 安装项目依赖:
   ```bash
   pip install -r requirements.txt
   ```

### 2. 配置环境变量

1. 复制`.env.example`文件为`.env`:
   ```bash
   cp .env.example .env
   ```

2. 编辑`.env`文件，配置必要的环境变量:
   ```
   SECRET_KEY=your-secret-key
   MAIL_SERVER=your-mail-server
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@example.com
   MAIL_PASSWORD=your-email-password
   MAIL_DEFAULT_SENDER=noreply@example.com
   ```

### 3. 配置Gunicorn

项目已包含`gunicorn_config.py`配置文件，您可以根据需要修改其中的参数:

```python
bind = "0.0.0.0:8000"  # 绑定地址和端口
workers = 4  # 工作进程数量，推荐设置为(2*CPU核心数+1)
```

### 4. 配置Nginx

1. 将项目中的`nginx_bioinfo.conf`文件复制到Nginx配置目录:
   ```bash
   # Linux
   sudo cp nginx_bioinfo.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/nginx_bioinfo.conf /etc/nginx/sites-enabled/
   ```

2. 编辑配置文件，替换其中的路径和域名:
   ```
   server_name yourdomain.com;
   location /static/ {
       alias /path/to/BioInfo-Nexus/front_html/;
   }
   ```

3. 测试并重启Nginx:
   ```bash
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### 5. 配置Supervisor (可选)

1. 将项目中的`supervisor_bioinfo.conf`文件复制到Supervisor配置目录:
   ```bash
   sudo cp supervisor_bioinfo.conf /etc/supervisor/conf.d/
   ```

2. 编辑配置文件，替换路径和用户名:
   ```
   directory=/path/to/BioInfo-Nexus
   command=/path/to/venv/bin/gunicorn -c gunicorn_config.py wsgi:application
   user=your-username
   ```

3. 重新加载Supervisor配置:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start bioinfo_nexus
   ```

### 6. 使用部署脚本

项目提供了自动部署脚本，您可以直接运行:

```bash
# Linux/macOS
chmod +x deploy.sh
./deploy.sh

# Windows
deploy.bat
```

## 故障排除

### 常见问题

1. **应用无法启动**
   - 检查日志文件: `logs/gunicorn_error.log`
   - 确保所有依赖都已安装
   - 验证环境变量是否正确配置

2. **静态文件无法加载**
   - 检查Nginx配置中的静态文件路径
   - 确保Nginx有权访问这些文件

3. **邮件发送失败**
   - 检查邮件服务器配置
   - 验证用户名和密码是否正确

## 安全注意事项

1. 确保生产环境中关闭Flask的调试模式
2. 使用HTTPS加密所有通信
3. 定期更新所有依赖包
4. 限制数据库访问权限
5. 定期备份数据库

## 性能优化

1. 增加Gunicorn工作进程数量（根据CPU核心数）
2. 配置Nginx缓存静态文件
3. 使用CDN分发静态资源
4. 监控应用性能，根据需要调整资源配置

## 监控和维护

1. 定期检查日志文件
2. 设置监控系统（如Prometheus + Grafana）
3. 配置警报通知
4. 定期更新系统和依赖

祝您部署顺利！如有问题，请联系项目维护者。 