<!-- docs/02-BACKEND.md -->
# 后端开发文档（FastAPI）

## 1. 技术栈
- Python 3.10+（建议 3.11）
- FastAPI + Uvicorn
- ORM：SQLAlchemy（或 SQLModel）
- 迁移：Alembic
- LLM 调用：硅基流动 API（兼容 OpenAI 格式）
- 向量库：Chroma（本地持久化）
- Embedding：硅基流动 BAAI/bge-large-zh-v1.5
- 重排序：硅基流动 rerank API

## 2. 目录结构（建议）
backend/
  app/
    main.py
    core/
      config.py
      auth.py
      logging.py
      exceptions.py
      deps.py
    api/
      v1/
        router.py
        auth.py
        kb.py
        qa.py
        rec.py
        analytics.py
    services/
      kb_service.py
      rag_service.py
      llm_client.py
      rec_service.py
      analytics_service.py
    kb/
      parser.py
      cleaner.py
      chunker.py
      embedder.py
      vectordb.py
      retriever.py
      reranker.py
    models/
      orm.py
      schemas.py
    db/
      session.py
      migrations/
  tests/

## 3. 服务边界
- api 层：只做请求校验、鉴权、调用 services
- services 层：业务编排（KB/RAG/REC/Analytics）
- kb 层：知识库管线实现（解析/切分/向量化/入库/检索）
- models：Pydantic schema + ORM model

## 4. 配置（core/config.py）
通过环境变量加载。必须支持：
- DATABASE_URL
- VECTORDB_TYPE=chroma
- CHROMA_PERSIST_DIR=./storage/chroma_db
- STORAGE_DIR
- SILICONFLOW_API_KEY
- SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
- EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
- LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
- JWT_SECRET
- CORS_ORIGINS

## 5. 错误处理约定
统一错误响应：
{
  "error": {
    "code": "KB_PARSE_FAILED",
    "message": "parse doc failed",
    "details": {...}
  }
}

- 4xx：用户输入或权限问题
- 5xx：服务内部异常
- 所有异常必须记录 request_id（middleware 注入）

## 6. 关键模块说明

### 6.1 KB Service
职责：
- upload：保存原文件，写 documents 表
- ingest：解析 -> 清洗 -> 切分 -> embedding -> upsert vectordb -> 写 chunks 表
- search：向量检索 + metadata filter（course_id）

要求：
- ingest 必须是异步任务（可先用 BackgroundTasks；生产用 Celery/RQ）
- 每个 chunk 必须有可追溯定位 meta（section/page/offset）

### 6.2 RAG Service
职责：
- query normalize/rewrite（可选）
- retrieve TopK（向量检索/混合检索）
- rerank（可选）
- prompt build（严格模板，带 citations）
- llm generate（支持 stream）

返回必须包含：
- answer
- citations（chunk_id, document, section, snippet）
- confidence（0-1）
- used_chunks（内部调试用）

### 6.3 Recommendation Service
职责：
- by_question：从 question/命中 chunks 映射知识点 -> 返回前置/例题/易错/下一步
- by_profile：结合学情（薄弱点）输出学习清单

### 6.4 Analytics Service
职责：
- event ingest：入库 events
- student profile：计算指标、薄弱点、风险等级、建议
- class dashboard：聚合统计、薄弱章节分布、预警名单

## 7. 性能约束（最小）
- kb/search p95 < 800ms（本地向量库）
- qa/ask 首 token < 2s（有缓存/无重排时）
- ingest 允许异步，前端通过 task_id 查询状态
