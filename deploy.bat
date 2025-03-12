@echo off
REM BioInfo Nexus Windows部署脚本

echo [INFO] 检查Python环境...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 未找到Python，请安装Python 3.8或更高版本
    exit /b 1
)

echo [INFO] 检查虚拟环境...
if not exist "venv\" (
    echo [INFO] 创建Python虚拟环境...
    python -m venv venv
)

echo [INFO] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [INFO] 安装依赖...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [INFO] 创建必要的目录...
if not exist "logs\" mkdir logs
if not exist "temp\" mkdir temp
if not exist "uploads\avatars\" mkdir uploads\avatars
if not exist "instance\" mkdir instance

echo [INFO] 检查配置文件...
if not exist ".env" (
    echo [WARN] 未找到.env文件，请确保已正确配置环境变量
)

echo [INFO] 使用Gunicorn启动应用...
gunicorn -c gunicorn_config.py wsgi:application

echo [INFO] 部署完成！ 