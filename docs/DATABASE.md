<!-- docs/03-DATABASE.md -->
# 数据库与存储（关系库 + 向量库）

## 1. 关系库（SQLite/PG）
### 1.1 表结构（最小可用）
users(
  id PK,
  username UNIQUE,
  password_hash,
  role,            -- student|teacher|admin
  created_at
)

courses(
  id PK,
  name,
  description,
  created_by FK(users.id),
  created_at
)

documents(
  id PK,
  course_id FK(courses.id),
  file_name,
  file_type,
  storage_path,
  status,          -- uploaded|processing|ready|failed
  created_at
)

chunks(
  id PK,
  document_id FK(documents.id),
  course_id FK(courses.id),
  chunk_index,
  chunk_text,
  meta_json,       -- {section, page, offset, title_path...}
  created_at
)

knowledge_points(
  id PK,
  course_id FK(courses.id),
  name,
  description,
  tags_json
)

kp_relations(
  id PK,
  course_id FK(courses.id),
  src_kp_id FK(knowledge_points.id),
  dst_kp_id FK(knowledge_points.id),
  relation_type,   -- prerequisite|related|contrast|example_of
  weight
)

qa_logs(
  id PK,
  user_id FK(users.id),
  course_id FK(courses.id),
  question,
  answer,
  citations_json,
  confidence,
  created_at
)

events(
  id PK,
  user_id FK(users.id),
  course_id FK(courses.id),
  event_type,
  payload_json,
  ts
)

alerts(
  id PK,
  user_id FK(users.id),
  course_id FK(courses.id),
  level,           -- low|medium|high
  reason,
  evidence_json,
  status,          -- open|ack|closed
  created_at
)

### 1.2 索引建议
- documents(course_id, status)
- chunks(course_id, document_id)
- events(user_id, course_id, ts)
- qa_logs(user_id, course_id, created_at)
- alerts(course_id, status, level)

## 2. 向量库（Chroma）
### 2.1 Chroma 配置
- 存储路径：./storage/chroma_db
- 集合名称：chunks_{course_id}
- 向量维度：1024（BAAI/bge-large-zh-v1.5）
- 距离度量：COSINE
- 持久化：本地文件系统

### 2.2 集合 Schema
Chroma使用灵活的文档存储模式：
```python
# 文档结构
{
    "id": "chunk_id",
    "document": "chunk_text",
    "metadata": {
        "course_id": "course_id",
        "document_id": "document_id", 
        "section": "section_name",
        "page": page_number
    },
    "embedding": [float_vector]  # 可选，可自动生成
}
```

### 2.3 适配器接口（必须统一）
- upsert(course_id, vectors: List[VectorRecord])
- query(course_id, query_text/query_embedding, top_k, filters) -> List[VectorHit]
- delete_by_document(course_id, document_id)
- create_collection(course_id)
- drop_collection(course_id)

VectorRecord：
- chunk_id: str
- course_id: str
- document_id: str
- section: str
- page: int
- chunk_text: str
- embedding: Optional[List[float]]  # 可选，Chroma可自动生成

VectorHit：
- chunk_id: str
- score: float (0-1，相似度分数)
- metadata: dict
- chunk_text: str

## 3. 文件存储（storage/）
- raw：原文件（上传）
- parsed：解析后结构化文本（json）
- cache：embedding/检索/回答缓存（可选）

命名建议：
storage/raw/{course_id}/{document_id}/{original_name}
storage/parsed/{document_id}.json
