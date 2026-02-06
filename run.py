#!/usr/bin/env python3
"""
原子物理智能课堂系统启动脚本
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

def check_requirements():
    """检查依赖是否安装"""
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'), 
        ('sqlalchemy', 'sqlalchemy'),
        ('chromadb', 'chromadb'),
        ('openai', 'openai'),
        ('pydantic', 'pydantic'),
        ('python-jose', 'jose'),  # 包名和导入名不同
        ('passlib', 'passlib')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"✗ 缺少依赖: {', '.join(missing_packages)}")
        print("请运行: pip install -r backend/requirements.txt")
        return False
    else:
        print("✓ 所有依赖已安装")
        return True

def setup_environment():
    """设置环境"""
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("✗ .env文件不存在")
        return False
    
    # 创建必要的目录
    directories = [
        "storage",
        "storage/raw", 
        "storage/parsed",
        "logs",
        "data"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✓ 环境设置完成")
    return True

def init_database():
    """初始化数据库"""
    try:
        from app.db.session import engine
        from app.models.orm import Base
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✓ 数据库初始化完成")
        return True
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return False

def create_default_user():
    """创建默认用户"""
    try:
        from app.db.session import SessionLocal
        from app.models.orm import User
        from app.core.auth import get_password_hash
        
        db = SessionLocal()
        
        # 检查是否已有管理员用户
        admin_user = db.query(User).filter(User.role == "admin").first()
        if admin_user:
            print("✓ 管理员用户已存在")
            db.close()
            return True
        
        # 创建默认管理员
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin)
        
        # 创建默认教师
        teacher = User(
            username="teacher",
            password_hash=get_password_hash("teacher123"),
            role="teacher"
        )
        db.add(teacher)
        
        # 创建默认学生
        student = User(
            username="student",
            password_hash=get_password_hash("student123"),
            role="student"
        )
        db.add(student)
        
        db.commit()
        db.close()
        
        print("✓ 默认用户创建完成")
        print("  管理员: admin / admin123")
        print("  教师: teacher / teacher123") 
        print("  学生: student / student123")
        return True
        
    except Exception as e:
        print(f"✗ 创建默认用户失败: {e}")
        return False

def create_default_course():
    """创建默认课程"""
    try:
        from app.db.session import SessionLocal
        from app.models.orm import Course, User
        
        db = SessionLocal()
        
        # 检查是否已有课程
        course = db.query(Course).first()
        if course:
            print("✓ 默认课程已存在")
            db.close()
            return True
        
        # 获取教师用户
        teacher = db.query(User).filter(User.role == "teacher").first()
        if not teacher:
            print("✗ 未找到教师用户")
            db.close()
            return False
        
        # 创建原子物理学课程
        course = Course(
            name="原子物理学",
            description="原子物理学基础课程，包含原子结构、波粒二象性、量子数等核心概念",
            created_by=teacher.id
        )
        db.add(course)
        db.commit()
        db.close()
        
        print("✓ 默认课程创建完成")
        return True
        
    except Exception as e:
        print(f"✗ 创建默认课程失败: {e}")
        return False

def start_backend():
    """启动后端服务"""
    try:
        os.chdir("backend")
        reload_enabled = os.getenv("UVICORN_RELOAD", "0").lower() in {"1", "true", "yes", "y"}
        cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        if reload_enabled:
            cmd.append("--reload")
        process = subprocess.Popen(cmd)
        os.chdir("..")
        return process
    except Exception as e:
        print(f"✗ 启动后端服务失败: {e}")
        return None

def start_frontend():
    """启动前端服务"""
    try:
        os.chdir("frontend")
        cmd = [sys.executable, "-m", "http.server", "3000"]
        process = subprocess.Popen(cmd)
        os.chdir("..")
        return process
    except Exception as e:
        print(f"✗ 启动前端服务失败: {e}")
        return None

def wait_for_service(url, timeout=30):
    """等待服务启动"""
    import requests
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def main():
    """主函数"""
    print("🚀 启动原子物理智能课堂系统")
    print("=" * 50)
    
    # 检查依赖
    if not check_requirements():
        return 1
    
    # 设置环境
    if not setup_environment():
        return 1
    
    # 初始化数据库
    if not init_database():
        return 1
    
    # 创建默认数据
    if not create_default_user():
        return 1
    
    if not create_default_course():
        return 1
    
    print("\n🔧 启动服务...")
    
    # 启动后端
    backend_process = start_backend()
    if not backend_process:
        return 1
    
    print("⏳ 等待后端服务启动...")
    if not wait_for_service("http://localhost:8000/health"):
        print("✗ 后端服务启动超时")
        backend_process.terminate()
        return 1
    
    print("✓ 后端服务启动成功 (http://localhost:8000)")
    
    # 启动前端
    frontend_process = start_frontend()
    if not frontend_process:
        backend_process.terminate()
        return 1
    
    print("⏳ 等待前端服务启动...")
    time.sleep(3)  # 简单等待
    
    print("✓ 前端服务启动成功 (http://localhost:3000)")
    
    print("\n🎉 系统启动完成!")
    print("=" * 50)
    print("📱 前端地址: http://localhost:3000")
    print("🔧 后端API: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("\n默认账户:")
    print("  管理员: admin / admin123")
    print("  教师: teacher / teacher123")
    print("  学生: student / student123")
    print("\n按 Ctrl+C 停止服务")
    
    # 等待中断信号
    def signal_handler(sig, frame):
        print("\n\n🛑 正在停止服务...")
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        print("✓ 服务已停止")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 等待进程结束
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())