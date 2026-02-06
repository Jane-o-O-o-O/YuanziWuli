# 技术集成文档

## 1. 硅基流动 API 集成

### 1.1 基础配置
```python
# 硅基流动客户端配置
SILICONFLOW_API_KEY = "sk-cnbodecqpwalpfwxklagcnrqtxukbiwkkblnobjnkkftavol"
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# 推荐模型配置
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"  # 中文向量模型
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"      # 对话模型
RERANK_MODEL = "BAAI/bge-reranker-large"     # 重排序模型
```

### 1.2 API 调用示例

#### 文本向量化
```python
import openai

client = openai.OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url=SILICONFLOW_BASE_URL
)

response = client.embeddings.create(
    model="BAAI/bge-large-zh-v1.5",
    input=["原子物理学中的波粒二象性"]
)
embedding = response.data[0].embedding
```

#### 对话生成
```python
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[
        {"role": "system", "content": "你是一个原子物理学专家"},
        {"role": "user", "content": "解释波粒二象性"}
    ],
    stream=True,
    temperature=0.7
)
```

#### 重排序
```python
import requests

rerank_response = requests.post(
    f"{SILICONFLOW_BASE_URL}/rerank",
    headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}"},
    json={
        "model": "BAAI/bge-reranker-large",
        "query": "波粒二象性的实验证据",
        "documents": [
            "双缝实验证明了光的波动性",
            "光电效应证明了光的粒子性",
            "电子衍射实验证明了物质波"
        ],
        "top_n": 3
    }
)
```

## 2. Chroma 集成

### 2.1 安装与配置
```bash
pip install chromadb
```

### 2.2 连接与集合管理
```python
import chromadb
from chromadb.config import Settings

# 连接 Chroma
client = chromadb.PersistentClient(
    path="./storage/chroma_db",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

# 创建或获取集合
def get_or_create_collection(course_id: str):
    collection_name = f"chunks_{course_id}"
    
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": f"原子物理课程{course_id}知识库"}
        )
    
    return collection
```

### 2.3 数据操作
```python
# 插入向量数据
def insert_chunks(collection, chunks_data: List[dict]):
    ids = [chunk["chunk_id"] for chunk in chunks_data]
    documents = [chunk["chunk_text"] for chunk in chunks_data]
    metadatas = [chunk["metadata"] for chunk in chunks_data]
    embeddings = [chunk["embedding"] for chunk in chunks_data]  # 可选
    
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings  # 如果不提供，Chroma会自动生成
    )

# 向量检索
def search_similar_chunks(collection, query_text: str, top_k: int = 12):
    results = collection.query(
        query_texts=[query_text],  # 或使用 query_embeddings
        n_results=top_k,
        where={"course_id": course_id},  # 过滤条件
        include=["documents", "metadatas", "distances"]
    )
    return results

# 删除文档
def delete_by_document(collection, document_id: str):
    results = collection.get(
        where={"document_id": document_id},
        include=["metadatas"]
    )
    
    if results['ids']:
        collection.delete(ids=results['ids'])
```

## 3. RAG 管线集成

### 3.1 完整 RAG 流程
```python
class RAGService:
    def __init__(self):
        self.siliconflow_client = openai.OpenAI(
            api_key=SILICONFLOW_API_KEY,
            base_url=SILICONFLOW_BASE_URL
        )
        self.milvus_collection = None
    
    async def ask_question(self, course_id: str, question: str) -> dict:
        # 1. 问题向量化
        query_embedding = await self.get_embedding(question)
        
        # 2. 向量检索
        collection = self.get_collection(course_id)
        search_results = search_similar_chunks(collection, query_embedding, top_k=12)
        
        # 3. 重排序（可选）
        if len(search_results[0]) > 6:
            reranked_results = await self.rerank_chunks(question, search_results[0][:12])
            final_chunks = reranked_results[:6]
        else:
            final_chunks = search_results[0]
        
        # 4. 构建 Prompt
        prompt = self.build_rag_prompt(question, final_chunks)
        
        # 5. LLM 生成
        response = await self.generate_answer(prompt)
        
        # 6. 计算置信度
        confidence = self.calculate_confidence(final_chunks, response)
        
        return {
            "answer": response["content"],
            "confidence": confidence,
            "citations": self.extract_citations(final_chunks),
            "used_chunks": len(final_chunks)
        }
    
    async def get_embedding(self, text: str) -> List[float]:
        response = self.siliconflow_client.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",
            input=[text]
        )
        return response.data[0].embedding
    
    def build_rag_prompt(self, question: str, chunks: List) -> str:
        evidence_text = "\n\n".join([
            f"[{i+1}] {chunk.entity.get('section', '')}: {chunk.entity.get('chunk_text', '')}"
            for i, chunk in enumerate(chunks)
        ])
        
        return f"""基于以下证据回答问题，必须提供引用标号。

证据：
{evidence_text}

问题：{question}

要求：
1. 只使用上述证据中的信息
2. 用 [1][2] 等标号标注引用
3. 如果证据不足，明确说明缺少什么信息
4. 回答要准确、完整、有逻辑性

回答："""
```

## 4. 性能优化建议

### 4.1 缓存策略
- 向量检索结果缓存（Redis）
- Embedding 结果缓存
- LLM 回答缓存（相同问题）

### 4.2 批处理优化
- 批量向量化文档
- 批量插入 Milvus
- 异步处理文档解析

### 4.3 监控指标
- API 调用延迟和成功率
- 向量检索性能
- 置信度分布
- 用户满意度反馈

## 5. 错误处理

### 5.1 硅基流动 API 错误
- 401: API Key 无效
- 429: 请求频率限制
- 500: 服务内部错误

### 5.2 Milvus 错误
- 连接失败
- 集合不存在
- 向量维度不匹配

### 5.3 降级策略
- API 失败时使用缓存结果
- 向量检索失败时使用关键词检索
- LLM 失败时返回检索结果摘要