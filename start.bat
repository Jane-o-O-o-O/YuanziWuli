@echo off
echo 启动原子物理智能课堂系统
echo ================================

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo 检查依赖...
python -c "import fastapi, uvicorn, sqlalchemy, pymilvus, openai" >nul 2>&1
if errorlevel 1 (
    echo 安装依赖中...
    pip install -r backend/requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖安装失败
        pause
        exit /b 1
    )
)

REM 启动系统
echo 启动系统...
python run.py

pause