#!/bin/bash

echo "启动原子物理智能课堂系统"
echo "================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.10+"
    exit 1
fi

# 检查依赖是否安装
echo "检查依赖..."
python3 -c "import fastapi, uvicorn, sqlalchemy, pymilvus, openai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装依赖中..."
    pip3 install -r backend/requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
fi

# 启动系统
echo "启动系统..."
python3 run.py