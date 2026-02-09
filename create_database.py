#!/usr/bin/env python3
"""
创建数据库脚本
用于在新环境中快速创建数据库和默认数据
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# 切换到backend目录，确保数据库文件创建在正确位置
os.chdir(backend_dir)

print("=" * 70)
print("原子物理智能课堂系统 - 数据库创建工具")
print("=" * 70)
print(f"\n当前工作目录: {os.getcwd()}")
print(f"数据库将创建在: {os.path.join(os.getcwd(), 'app.db')}\n")

def create_tables():
    """创建数据库表"""
    print("步骤 1/3: 创建数据库表...")
    try:
        from app.db.session import engine
        from app.models.orm import Base
        
        # 删除所有表（如果存在）
        Base.metadata.drop_all(bind=engine)
        print("  - 已清理旧表")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("  ✓ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"  ✗ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_users():
    """创建默认用户"""
    print("\n步骤 2/3: 创建默认用户...")
    try:
        from app.db.session import SessionLocal
        from app.models.orm import User
        from app.core.auth import get_password_hash
        
        db = SessionLocal()
        
        # 定义默认用户
        default_users = [
            {
                "username": "admin",
                "password": "admin123",
                "role": "admin",
                "description": "管理员"
            },
            {
                "username": "teacher",
                "password": "teacher123",
                "role": "teacher",
                "description": "教师"
            },
            {
                "username": "student",
                "password": "student123",
                "role": "student",
                "description": "学生"
            }
        ]
        
        # 创建用户
        for user_data in default_users:
            user = User(
                username=user_data["username"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"]
            )
            db.add(user)
            print(f"  - 创建用户: {user_data['username']} / {user_data['password']} ({user_data['description']})")
        
        db.commit()
        
        # 验证用户创建
        user_count = db.query(User).count()
        print(f"  ✓ 成功创建 {user_count} 个用户")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"  ✗ 创建用户失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_course():
    """创建默认课程"""
    print("\n步骤 3/3: 创建默认课程...")
    try:
        from app.db.session import SessionLocal
        from app.models.orm import Course, User
        
        db = SessionLocal()
        
        # 获取教师用户
        teacher = db.query(User).filter(User.role == "teacher").first()
        if not teacher:
            print("  ✗ 未找到教师用户")
            db.close()
            return False
        
        # 创建课程
        course = Course(
            name="原子物理学",
            description="原子物理学基础课程，包含原子结构、波粒二象性、量子数等核心概念",
            created_by=teacher.id
        )
        db.add(course)
        db.commit()
        
        print(f"  - 创建课程: {course.name}")
        print(f"  ✓ 课程创建成功")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"  ✗ 创建课程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_database():
    """验证数据库"""
    print("\n" + "=" * 70)
    print("验证数据库...")
    print("=" * 70)
    try:
        from app.db.session import SessionLocal
        from app.models.orm import User, Course
        from app.core.auth import verify_password
        
        db = SessionLocal()
        
        # 检查用户
        users = db.query(User).all()
        print(f"\n用户列表 (共 {len(users)} 个):")
        for user in users:
            print(f"  - {user.username} ({user.role})")
        
        # 检查课程
        courses = db.query(Course).all()
        print(f"\n课程列表 (共 {len(courses)} 个):")
        for course in courses:
            print(f"  - {course.name}")
        
        # 测试认证
        print("\n测试用户认证:")
        test_user = db.query(User).filter(User.username == "student").first()
        if test_user:
            is_valid = verify_password("student123", test_user.password_hash)
            print(f"  - student/student123 认证: {'✓ 成功' if is_valid else '✗ 失败'}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ 验证失败: {e}")
        return False

def main():
    """主函数"""
    success = True
    
    # 创建表
    if not create_tables():
        success = False
    
    # 创建用户
    if success and not create_users():
        success = False
    
    # 创建课程
    if success and not create_course():
        success = False
    
    # 验证数据库
    if success:
        verify_database()
    
    # 返回项目根目录
    os.chdir(Path(__file__).parent)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 数据库创建完成！")
        print("=" * 70)
        print("\n默认账户:")
        print("  管理员: admin / admin123")
        print("  教师:   teacher / teacher123")
        print("  学生:   student / student123")
        print("\n现在可以运行 'python run.py' 启动系统")
    else:
        print("❌ 数据库创建失败，请检查错误信息")
        print("=" * 70)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
