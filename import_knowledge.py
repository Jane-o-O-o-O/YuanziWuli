#!/usr/bin/env python3
"""
知识库批量导入脚本
用于将原子物理学教案批量导入到知识库
"""

import sys
import os
import asyncio
from pathlib import Path

# 自动检测项目根目录（脚本所在目录）
project_root = Path(__file__).parent.resolve()
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 切换到backend目录
os.chdir(backend_dir)

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.orm import Course, Document
from app.services.kb_service import kb_service

# 教案文件夹路径
TEACHING_MATERIALS_DIR = project_root / "原子物理学-教案"

# 支持的文件类型
SUPPORTED_EXTENSIONS = {
    '.pdf': 'pdf',
    '.docx': 'docx',
    '.pptx': 'pptx',
    '.md': 'md',
    '.txt': 'txt'
}


async def import_document(db: Session, course_id: int, file_path: Path):
    """导入单个文档"""
    try:
        # 读取文件
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        file_name = file_path.name
        file_ext = file_path.suffix.lower()
        file_type = SUPPORTED_EXTENSIONS.get(file_ext)
        
        if not file_type:
            print(f"  ⊘ 跳过不支持的文件类型: {file_name}")
            return None
        
        print(f"  → 上传文档: {file_name} ({len(file_content) / 1024:.1f} KB)")
        
        # 上传文档
        document = await kb_service.upload_document(
            db=db,
            course_id=course_id,
            file_name=file_name,
            file_content=file_content,
            file_type=file_type
        )
        
        print(f"  ✓ 上传成功，文档ID: {document.id}")
        
        # 开始入库处理
        print(f"  → 开始处理文档...")
        task_id = await kb_service.ingest_document(
            db=db,
            document_id=document.id
        )
        
        print(f"  ✓ 入库任务已创建: {task_id}")
        
        # 等待任务完成
        max_wait = 300  # 最多等待5分钟
        wait_time = 0
        while wait_time < max_wait:
            await asyncio.sleep(2)
            wait_time += 2
            
            task_status = await kb_service.get_task_status(db, task_id)
            status = task_status['status']
            progress = task_status.get('progress', 0)
            
            if status == 'done':
                print(f"  ✓ 文档处理完成: {file_name}")
                return document
            elif status == 'failed':
                error = task_status.get('error', '未知错误')
                print(f"  ✗ 文档处理失败: {error}")
                return None
            else:
                print(f"  ⏳ 处理中... {progress * 100:.0f}%", end='\r')
        
        print(f"  ⚠ 处理超时: {file_name}")
        return None
        
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def import_all_documents():
    """批量导入所有文档"""
    print("=" * 80)
    print("原子物理智能课堂系统 - 知识库批量导入")
    print("=" * 80)
    print(f"\n项目根目录: {project_root}")
    print(f"教案目录: {TEACHING_MATERIALS_DIR}")
    print(f"当前工作目录: {os.getcwd()}\n")
    
    # 检查教案目录
    if not TEACHING_MATERIALS_DIR.exists():
        print(f"✗ 教案目录不存在: {TEACHING_MATERIALS_DIR}")
        return
    
    # 获取所有支持的文件
    files_to_import = []
    for ext in SUPPORTED_EXTENSIONS.keys():
        files_to_import.extend(TEACHING_MATERIALS_DIR.glob(f"*{ext}"))
    
    if not files_to_import:
        print("✗ 未找到可导入的文件")
        return
    
    print(f"找到 {len(files_to_import)} 个文件待导入:\n")
    for i, file_path in enumerate(files_to_import, 1):
        file_size = file_path.stat().st_size / 1024
        print(f"  {i}. {file_path.name} ({file_size:.1f} KB)")
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 获取课程
        course = db.query(Course).filter(Course.name == "原子物理学").first()
        if not course:
            print("\n✗ 未找到'原子物理学'课程，请先运行 create_database.py 创建数据库")
            return
        
        print(f"\n目标课程: {course.name} (ID: {course.id})")
        
        # 检查已导入的文档
        existing_docs = db.query(Document).filter(Document.course_id == course.id).all()
        existing_names = {doc.file_name for doc in existing_docs}
        
        if existing_names:
            print(f"\n已导入的文档 ({len(existing_names)} 个):")
            for name in existing_names:
                print(f"  - {name}")
            
            response = input("\n是否清空已有文档重新导入？(y/N): ").strip().lower()
            if response == 'y':
                print("\n清空已有文档...")
                for doc in existing_docs:
                    await kb_service.delete_document(db, doc.id)
                    print(f"  - 已删除: {doc.file_name}")
                existing_names.clear()
        
        # 开始导入
        print("\n" + "=" * 80)
        print("开始批量导入")
        print("=" * 80 + "\n")
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, file_path in enumerate(files_to_import, 1):
            print(f"\n[{i}/{len(files_to_import)}] {file_path.name}")
            print("-" * 80)
            
            # 跳过已导入的文档
            if file_path.name in existing_names:
                print(f"  ⊘ 已存在，跳过")
                skipped_count += 1
                continue
            
            # 导入文档
            result = await import_document(db, course.id, file_path)
            
            if result:
                success_count += 1
            else:
                failed_count += 1
            
            # 刷新数据库会话
            db.commit()
        
        # 统计结果
        print("\n" + "=" * 80)
        print("导入完成")
        print("=" * 80)
        print(f"\n总计: {len(files_to_import)} 个文件")
        print(f"  ✓ 成功: {success_count}")
        print(f"  ✗ 失败: {failed_count}")
        print(f"  ⊘ 跳过: {skipped_count}")
        
        # 显示最终状态
        all_docs = db.query(Document).filter(Document.course_id == course.id).all()
        ready_docs = [d for d in all_docs if d.status == 'ready']
        
        print(f"\n知识库状态:")
        print(f"  总文档数: {len(all_docs)}")
        print(f"  就绪文档: {len(ready_docs)}")
        
    finally:
        db.close()


def main():
    """主函数"""
    try:
        asyncio.run(import_all_documents())
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断导入")
    except Exception as e:
        print(f"\n✗ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
