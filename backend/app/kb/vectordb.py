from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import logging
import chromadb
from chromadb.config import Settings
import uuid

from app.core.config import settings
from app.core.exceptions import VectorDBException

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    """向量记录"""
    chunk_id: str
    course_id: str
    document_id: str
    section: str
    page: int
    chunk_text: str
    embedding: Optional[List[float]] = None  # Chroma可以自动生成embedding


@dataclass
class VectorHit:
    """向量检索结果"""
    chunk_id: str
    score: float
    metadata: Dict[str, Any]
    chunk_text: str


class ChromaAdapter:
    """Chroma向量数据库适配器"""
    
    def __init__(self, embedding_fn: Optional[Callable[[str], List[float]]] = None):
        self.embedding_fn = embedding_fn
        self.client = None
        self.connected = False

    def _backup_and_reset_persist_dir(self, persist_dir: str) -> bool:
        """备份并重置持久化目录"""
        import os
        import shutil
        from datetime import datetime

        backup_dir = f"{persist_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            if os.path.exists(persist_dir):
                shutil.move(persist_dir, backup_dir)
                logger.info(f"已备份损坏的数据库到: {backup_dir}")
            os.makedirs(persist_dir, exist_ok=True)
            return True
        except Exception as backup_error:
            logger.error(f"备份数据库失败: {backup_error}")
            return False
        
    async def init_connection(self):
        """初始化连接"""
        try:
            import os
            persist_dir = os.path.abspath(settings.CHROMA_PERSIST_DIR)

            os.makedirs(persist_dir, exist_ok=True)
            
            logger.info(f"Chroma目录: {persist_dir}")
            
            # 最简单的方式创建客户端
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.connected = True
            
            # 测试连接
            collections = self.client.list_collections()
            logger.info(f"Chroma连接成功，现有{len(collections)}个集合")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Chroma连接失败: {e}")
            
            # 检查是否是schema不兼容错误
            if "no such column: collections.topic" in error_msg:
                logger.warning("检测到ChromaDB schema不兼容，备份并重建数据库...")
                try:
                    self.connected = False
                    ok = self._backup_and_reset_persist_dir(persist_dir)
                    if not ok:
                        raise VectorDBException(
                            "ChromaDB schema不兼容，且数据库文件被占用无法备份/重建。"
                            "请先停止后端服务，确保没有 python/uvicorn 进程占用后，"
                            "手动删除 storage/chroma_db 并重新导入知识库。"
                        )
                    # 重新创建客户端
                    self.client = chromadb.PersistentClient(path=persist_dir)
                    self.connected = True
                    collections = self.client.list_collections()
                    logger.info(f"ChromaDB重建成功，现有{len(collections)}个集合")
                    return
                except Exception as reset_error:
                    logger.error(f"重建ChromaDB失败: {reset_error}")
                    raise VectorDBException(f"向量数据库连接失败且无法自动恢复: {reset_error}")
            
            raise VectorDBException(f"向量数据库连接失败: {e}")
    
    def _get_collection_name(self, course_id: str) -> str:
        """获取集合名称"""
        return f"chunks_{course_id}"
    
    async def create_collection(self, course_id: str):
        """创建集合"""
        if not self.connected:
            await self.init_connection()
        
        collection_name = self._get_collection_name(course_id)
        
        try:
            # 尝试获取现有集合
            try:
                collection = self.client.get_collection(collection_name)
                logger.info(f"集合已存在: {collection_name}")
                return collection
            except Exception:
                # 集合不存在，创建新集合
                pass
            
            # 创建新集合 - 不使用默认embedding函数，我们自己提供embedding
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": f"原子物理课程{course_id}知识库"},
                embedding_function=None  # 关键：不使用默认embedding函数
            )
            
            logger.info(f"集合创建成功: {collection_name}")
            return collection
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise VectorDBException(f"创建向量集合失败: {e}")
    
    async def get_collection(self, course_id: str):
        """获取集合"""
        collection_name = self._get_collection_name(course_id)
        
        try:
            if not self.connected:
                await self.init_connection()
            
            try:
                collection = self.client.get_collection(collection_name)
                count = collection.count()
                logger.info(f"获取集合成功: {collection_name}, 向量数: {count}")
                return collection
            except Exception as e:
                # 集合不存在
                logger.error(f"集合不存在: {collection_name}, 错误: {e}")
                # 尝试创建集合（但这应该只在导入数据时发生）
                logger.warning(f"尝试创建新集合: {collection_name}")
                return await self.create_collection(course_id)
                
        except Exception as e:
            logger.error(f"获取集合失败: {e}")
            raise VectorDBException(f"获取向量集合失败: {e}")
    
    async def upsert(self, course_id: str, vectors: List[VectorRecord]):
        """插入或更新向量"""
        if not vectors:
            return
        
        try:
            collection = await self.get_collection(course_id)
            
            # 准备数据
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for vector in vectors:
                ids.append(vector.chunk_id)
                documents.append(vector.chunk_text)
                metadatas.append({
                    "course_id": vector.course_id,
                    "document_id": vector.document_id,
                    "section": vector.section,
                    "page": vector.page
                })
                
                # 如果提供了embedding，使用它；否则让Chroma自动生成
                if vector.embedding:
                    embeddings.append(vector.embedding)
                elif self.embedding_fn:
                    embeddings.append(self.embedding_fn(vector.chunk_text))
            
            # 插入数据
            if embeddings:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                # 让Chroma自动生成embedding
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            logger.info(f"向量插入成功: {len(vectors)} 条记录")
            
        except Exception as e:
            logger.error(f"向量插入失败: {e}")
            raise VectorDBException(f"向量插入失败: {e}")
    
    async def query(
        self,
        course_id: str,
        query_text: str = None,
        query_embedding: List[float] = None,
        top_k: int = 12,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorHit]:
        """向量检索"""
        try:
            collection = await self.get_collection(course_id)

            # 构建过滤条件 - 暂时不使用course_id过滤，因为集合名已经包含了course_id
            where_filter = None
            if filters:
                where_filter = {}
                if "document_id" in filters:
                    where_filter["document_id"] = filters["document_id"]
                if "section" in filters:
                    where_filter["section"] = {"$contains": filters["section"]}

            # 执行检索
            if query_embedding:
                # 使用提供的embedding
                logger.info(f"使用embedding查询，维度: {len(query_embedding)}, top_k: {top_k}, where: {where_filter}")

                # 根据是否有过滤条件决定是否传where参数
                if where_filter:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=top_k,
                        where=where_filter,
                        include=["documents", "metadatas", "distances"]
                    )
                else:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=top_k,
                        include=["documents", "metadatas", "distances"]
                    )

                logger.info(f"Chroma返回结果: ids={len(results.get('ids', [[]])[0]) if results.get('ids') else 0}")
            elif query_text:
                # 使用文本查询
                if self.embedding_fn:
                    query_embedding = self.embedding_fn(query_text)
                    if where_filter:
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=top_k,
                            where=where_filter,
                            include=["documents", "metadatas", "distances"]
                        )
                    else:
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=top_k,
                            include=["documents", "metadatas", "distances"]
                        )
                else:
                    # 让Chroma自动处理
                    if where_filter:
                        results = collection.query(
                            query_texts=[query_text],
                            n_results=top_k,
                            where=where_filter,
                            include=["documents", "metadatas", "distances"]
                        )
                    else:
                        results = collection.query(
                            query_texts=[query_text],
                            n_results=top_k,
                            include=["documents", "metadatas", "distances"]
                        )
            else:
                raise ValueError("必须提供 query_text 或 query_embedding")

            # 转换结果
            logger.info(f"results类型: {type(results)}, keys: {results.keys() if hasattr(results, 'keys') else 'N/A'}")
            logger.info(f"results['ids']: {results.get('ids', 'N/A')}")

            hits = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    # Chroma返回的是距离，需要转换为相似度分数
                    distance = results['distances'][0][i]
                    # 将距离转换为相似度分数 (0-1)，距离越小相似度越高
                    score = max(0, 1 - distance)

                    hit = VectorHit(
                        chunk_id=results['ids'][0][i],
                        score=score,
                        metadata=results['metadatas'][0][i],
                        chunk_text=results['documents'][0][i]
                    )
                    hits.append(hit)

            logger.info(f"向量检索成功: 返回 {len(hits)} 条结果")
            return hits

        except Exception as e:
            error_msg = str(e)
            logger.error(f"向量检索失败: {e}")

            # 检查是否是数据库损坏的错误
            if "Cannot open header file" in error_msg or "corrupted" in error_msg.lower():
                raise VectorDBException(
                    "向量数据库文件无法打开（可能被占用或已损坏）。"
                    "请先停止后端服务，确保没有其它进程占用 storage/chroma_db/chroma.sqlite3，"
                    "然后手动删除 storage/chroma_db 并重新导入知识库。"
                )

            raise VectorDBException(f"向量检索失败: {e}")
    
    async def delete_by_document(self, course_id: str, document_id: str):
        """根据文档ID删除向量"""
        try:
            collection = await self.get_collection(course_id)
            
            # 查找要删除的文档
            results = collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            
            if results['ids']:
                # 删除找到的文档
                collection.delete(ids=results['ids'])
                logger.info(f"文档向量删除成功: {document_id}, 删除了 {len(results['ids'])} 条记录")
            else:
                logger.info(f"未找到文档 {document_id} 的向量记录")
            
        except Exception as e:
            logger.error(f"文档向量删除失败: {e}")
            raise VectorDBException(f"文档向量删除失败: {e}")
    
    async def drop_collection(self, course_id: str):
        """删除集合"""
        collection_name = self._get_collection_name(course_id)
        
        try:
            if not self.connected:
                await self.init_connection()
                
            self.client.delete_collection(collection_name)
            logger.info(f"集合删除成功: {collection_name}")
            
        except Exception as e:
            logger.error(f"集合删除失败: {e}")
            raise VectorDBException(f"集合删除失败: {e}")
    
    async def get_collection_stats(self, course_id: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            collection = await self.get_collection(course_id)
            count = collection.count()
            
            return {
                "collection_name": self._get_collection_name(course_id),
                "row_count": count,
                "data_size": count * 1024  # 估算大小
            }
            
        except Exception as e:
            logger.error(f"获取集合统计失败: {e}")
            return {"error": str(e)}


class MilvusAdapter:
    """保留原有的MilvusAdapter以兼容旧代码"""
    
    def __init__(self):
        raise NotImplementedError("MilvusAdapter已弃用，请使用ChromaAdapter")


# 向量数据库适配器工厂
def create_vectordb_adapter(embedding_fn: Optional[Callable[[str], List[float]]] = None):
    """创建向量数据库适配器"""
    if settings.VECTORDB_TYPE.lower() == "chroma":
        return ChromaAdapter(embedding_fn=embedding_fn)
    elif settings.VECTORDB_TYPE.lower() == "milvus-lite":
        raise NotImplementedError("Milvus Lite已弃用，请使用Chroma")
    else:
        raise ValueError(f"不支持的向量数据库类型: {settings.VECTORDB_TYPE}")