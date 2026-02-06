import os
import uuid
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import KBUploadFailedException, KBIngestFailedException, TaskNotFoundException
from app.models.orm import Document, Chunk, IngestTask
from app.models.schemas import ChunkPolicy
from app.kb.parser import DocumentParser
from app.kb.chunker import TextChunker
from app.kb.vectordb import create_vectordb_adapter, VectorRecord
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


class KBService:
    """知识库服务"""
    
    def __init__(self):
        # 创建embedding函数
        async def embedding_fn(text: str) -> List[float]:
            result = await llm_client.get_embedding(text)
            return result.embedding
        
        self.embedding_fn = embedding_fn
        self.vectordb = create_vectordb_adapter(embedding_fn=None)  # 我们会在异步方法中处理embedding
        self.parser = DocumentParser()
    
    async def upload_document(
        self,
        db: Session,
        course_id: int,
        file_name: str,
        file_content: bytes,
        file_type: str
    ) -> Document:
        """上传文档"""
        try:
            # 验证文件类型
            if file_type.lower() not in [ft.lower() for ft in settings.ALLOWED_FILE_TYPES]:
                raise KBUploadFailedException(f"不支持的文件类型: {file_type}")
            
            # 验证文件大小
            if len(file_content) > settings.get_max_file_size_bytes():
                raise KBUploadFailedException(
                    f"文件过大: {len(file_content)} bytes, 最大允许: {settings.get_max_file_size_bytes()} bytes"
                )
            
            # 生成存储路径
            doc_id = str(uuid.uuid4())
            storage_path = f"{settings.STORAGE_DIR}/raw/{course_id}/{doc_id}_{file_name}"
            
            # 确保目录存在
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            # 保存文件
            with open(storage_path, 'wb') as f:
                f.write(file_content)
            
            # 创建数据库记录
            document = Document(
                course_id=course_id,
                file_name=file_name,
                file_type=file_type,
                storage_path=storage_path,
                status="uploaded"
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"文档上传成功: {file_name} -> {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"文档上传失败: {e}")
            raise KBUploadFailedException(f"文档上传失败: {e}")
    
    async def ingest_document(
        self,
        db: Session,
        document_id: int,
        chunk_policy: Optional[ChunkPolicy] = None
    ) -> str:
        """异步入库文档"""
        # 创建任务记录
        task_id = str(uuid.uuid4())
        task = IngestTask(
            task_id=task_id,
            document_id=document_id,
            status="queued"
        )
        
        db.add(task)
        db.commit()
        
        # 启动后台任务
        asyncio.create_task(self._ingest_document_task(task_id, document_id, chunk_policy))
        
        logger.info(f"文档入库任务创建: {task_id}")
        return task_id
    
    async def _ingest_document_task(
        self,
        task_id: str,
        document_id: int,
        chunk_policy: Optional[ChunkPolicy] = None
    ):
        """文档入库任务"""
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            # 更新任务状态
            task = db.query(IngestTask).filter(IngestTask.task_id == task_id).first()
            if not task:
                return
            
            task.status = "processing"
            task.progress = 0.1
            db.commit()
            
            # 获取文档信息
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise Exception("文档不存在")
            
            # 解析文档
            logger.info(f"开始解析文档: {document.file_name}")
            parsed_doc = self.parser.parse_file(document.storage_path, document.file_type)
            
            # 保存解析结果
            parsed_path = f"{settings.STORAGE_DIR}/parsed/{document_id}.json"
            os.makedirs(os.path.dirname(parsed_path), exist_ok=True)
            with open(parsed_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_doc, f, ensure_ascii=False, indent=2)
            
            task.progress = 0.3
            db.commit()
            
            # 文本分块
            logger.info(f"开始文本分块: {document.file_name}")
            chunker = TextChunker(
                chunk_size=chunk_policy.max_chars if chunk_policy else settings.CHUNK_SIZE,
                overlap=chunk_policy.overlap if chunk_policy else settings.CHUNK_OVERLAP
            )
            chunks = chunker.chunk_document(parsed_doc)
            
            task.progress = 0.5
            db.commit()
            
            # 向量化
            logger.info(f"开始向量化: {len(chunks)} 个文本块")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = await llm_client.get_embeddings_batch(chunk_texts)
            
            task.progress = 0.7
            db.commit()
            
            # 保存到数据库和向量库
            logger.info(f"保存到数据库和向量库")
            vector_records = []
            
            for i, (chunk, embedding_result) in enumerate(zip(chunks, embeddings)):
                # 保存到关系数据库
                chunk_record = Chunk(
                    document_id=document_id,
                    course_id=document.course_id,
                    chunk_index=chunk.index,
                    chunk_text=chunk.text,
                    meta_json=chunk.metadata
                )
                db.add(chunk_record)
                db.flush()  # 获取ID
                
                # 准备向量记录
                vector_record = VectorRecord(
                    chunk_id=str(chunk_record.id),
                    course_id=str(document.course_id),
                    document_id=str(document_id),
                    section=chunk.metadata.get("section", ""),
                    page=chunk.metadata.get("page", 0),
                    chunk_text=chunk.text[:2000],  # 限制长度
                    embedding=embedding_result.embedding  # 使用获取的embedding
                )
                vector_records.append(vector_record)
            
            # 批量插入向量库
            await self.vectordb.upsert(str(document.course_id), vector_records)
            
            # 更新文档状态
            document.status = "ready"
            task.status = "done"
            task.progress = 1.0
            
            db.commit()
            
            logger.info(f"文档入库完成: {document.file_name}, {len(chunks)} 个文本块")
            
        except Exception as e:
            logger.error(f"文档入库失败: {e}")
            
            # 更新任务状态
            if task:
                task.status = "failed"
                task.error_message = str(e)
                db.commit()
            
            # 更新文档状态
            if document:
                document.status = "failed"
                db.commit()
                
        finally:
            db.close()
    
    async def get_task_status(self, db: Session, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        task = db.query(IngestTask).filter(IngestTask.task_id == task_id).first()
        
        if not task:
            raise TaskNotFoundException(task_id)
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "error": task.error_message
        }
    
    async def search_knowledge(
        self,
        course_id: int,
        query: str,
        top_k: int = 12,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            # 获取查询向量
            embedding_result = await llm_client.get_embedding(query)
            
            # 向量检索 - 使用embedding而不是文本，因为我们的ChromaAdapter需要embedding
            hits = await self.vectordb.query(
                course_id=str(course_id),
                query_embedding=embedding_result.embedding,
                top_k=top_k,
                filters=filters
            )
            
            # 转换结果格式
            results = []
            for hit in hits:
                results.append({
                    "chunk_id": int(hit.chunk_id),
                    "score": hit.score,
                    "document_id": int(hit.metadata["document_id"]),
                    "meta": hit.metadata,
                    "snippet": hit.chunk_text[:200] + "..." if len(hit.chunk_text) > 200 else hit.chunk_text
                })
            
            logger.info(f"知识检索完成: 查询='{query}', 结果数={len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"知识检索失败: {e}")
            raise KBIngestFailedException(f"知识检索失败: {e}")
    
    async def delete_document(self, db: Session, document_id: int):
        """删除文档"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
            
            # 删除向量数据
            await self.vectordb.delete_by_document(str(document.course_id), str(document_id))
            
            # 删除文本块记录
            db.query(Chunk).filter(Chunk.document_id == document_id).delete()
            
            # 删除文档记录
            db.delete(document)
            
            # 删除文件
            if os.path.exists(document.storage_path):
                os.remove(document.storage_path)
            
            parsed_path = f"{settings.STORAGE_DIR}/parsed/{document_id}.json"
            if os.path.exists(parsed_path):
                os.remove(parsed_path)
            
            db.commit()
            
            logger.info(f"文档删除成功: {document_id}")
            
        except Exception as e:
            logger.error(f"文档删除失败: {e}")
            raise KBIngestFailedException(f"文档删除失败: {e}")


# 全局服务实例
kb_service = KBService()