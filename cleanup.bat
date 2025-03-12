@echo off
echo ==== BioInfo Nexus 项目清理工具 ====

set /p confirm=确定要清理项目中的临时文件吗? (Y/N): 
if /i not "%confirm%"=="Y" goto :end

echo.
echo [INFO] 删除Python缓存文件...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc *.pyo >nul 2>&1

echo [INFO] 删除IDE配置文件夹...
if exist ".idea" rmdir /s /q .idea
if exist ".vscode" rmdir /s /q .vscode

echo [INFO] 清理临时文件...
if exist "temp" del /q temp\*.* >nul 2>&1

echo [INFO] 清理日志文件...
if exist "logs" del /q logs\*.* >nul 2>&1
del /q app.log >nul 2>&1

echo.
echo [INFO] 清理完成!
echo.

echo ==== 可选操作 ====
echo 以下操作可能会删除重要文件，请谨慎选择。

set /p delete_uploads=是否清空uploads文件夹? (Y/N): 
if /i "%delete_uploads%"=="Y" (
    if exist "uploads" (
        del /q /s uploads\*.* >nul 2>&1
        echo [INFO] uploads文件夹已清空
    )
)

set /p delete_db=是否删除数据库文件? (Y/N): 
if /i "%delete_db%"=="Y" (
    if exist "instance\bioinfo_nexus.db" (
        del /q instance\bioinfo_nexus.db >nul 2>&1
        echo [INFO] 数据库文件已删除
    )
)

set /p recreate_venv=是否删除并重建虚拟环境? (Y/N): 
if /i "%recreate_venv%"=="Y" (
    if exist "venv" (
        echo [INFO] 删除虚拟环境...
        rmdir /s /q venv
        echo [INFO] 创建新的虚拟环境...
        python -m venv venv
        echo [INFO] 虚拟环境已重建
    )
)

:end
echo.
echo 按任意键退出...
pause >nul 