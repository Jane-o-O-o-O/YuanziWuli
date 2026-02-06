<!-- docs/05-API-SPEC.md -->
# API 规格（REST + WS）

## 0. 约定
Base：`/api/v1`
Auth：`Authorization: Bearer <token>`
错误响应统一：
{
  "error": { "code": "...", "message": "...", "details": {} }
}

## 1. Auth
### POST /auth/login
req:
{ "username": "u", "password": "p" }
resp:
{ "access_token": "...", "role": "student" }

### GET /auth/me
resp:
{ "id":"...", "username":"...", "role":"..." }

## 2. Knowledge Base
### POST /kb/upload (multipart)
form:
- file: <binary>
- course_id: string
resp:
{ "document_id":"...", "status":"uploaded" }

### POST /kb/ingest
req:
{ "document_id":"...", "chunk_policy": { "max_chars": 800, "overlap": 120 } }
resp:
{ "task_id":"...", "status":"queued" }

### GET /kb/tasks/{task_id}
resp:
{ "task_id":"...", "status":"processing|done|failed", "progress": 0.0, "error": null }

### GET /kb/search?q=...&course_id=...
resp:
{
  "hits":[
    {
      "chunk_id":"...",
      "score":0.82,
      "document_id":"...",
      "meta":{ "section":"...", "page": 12 },
      "snippet":"..."
    }
  ]
}

## 3. QA
### POST /qa/ask
req:
{ "course_id":"...", "question":"...", "top_k": 12 }
resp:
{
  "qa_id":"...",
  "answer":"...",
  "confidence":0.73,
  "citations":[
    { "chunk_id":"...", "document_id":"...", "section":"...", "snippet":"..." }
  ],
  "followups":[ "..." ]
}

### POST /qa/feedback
req:
{ "qa_id":"...", "rating": 1 }   # 1=like, -1=dislike
resp:
{ "ok": true }

### WS /qa/stream
message in:
{ "course_id":"...", "question":"..." }
message out (server):
- { "type":"delta", "text":"..." }
- { "type":"final", "qa_id":"...", "confidence":..., "citations":[...] }

## 4. Recommendation
### GET /rec/by_question?q=...&course_id=...
resp:
{ "prerequisites":[...], "examples":[...], "pitfalls":[...], "next_steps":[...] }

### GET /rec/by_profile?user_id=...&course_id=...
resp:
{ "plan":[ { "kp":"...", "actions":[...] } ] }

## 5. Analytics
### POST /analytics/event
req:
{ "user_id":"...", "course_id":"...", "event_type":"ask", "payload":{}, "ts":"..." }
resp:
{ "ok": true }

### GET /analytics/student/{user_id}?course_id=...
resp:
{
  "active_7d": 32,
  "weak_kp":[ { "kp":"...", "score":0.81 } ],
  "risk_level":"medium",
  "reasons":[ "..." ],
  "suggestions":[ "..." ]
}

### GET /analytics/class/{course_id}
resp:
{
  "weak_kp_dist":[ { "kp":"...", "count": 18 } ],
  "alerts":[ { "user_id":"...", "level":"high", "reason":"..." } ]
}

## 6. 错误码（最小）
- AUTH_INVALID
- PERMISSION_DENIED
- KB_UPLOAD_FAILED
- KB_PARSE_FAILED
- KB_INGEST_FAILED
- VECTORDB_ERROR
- LLM_ERROR
- QA_LOW_CONFIDENCE
- ANALYTICS_ERROR
