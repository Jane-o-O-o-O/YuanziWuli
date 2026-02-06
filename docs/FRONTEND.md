<!-- docs/01-FRONTEND.md -->
# 前端开发文档（HTML/CSS/JS）

## 1. 技术栈
- 原生 HTML + CSS + JavaScript
- 图表：ECharts（可选）
- 与后端交互：fetch（REST），可选 WebSocket（流式回答）

## 2. 目录结构（建议）
frontend/
  index.html
  pages/
    login.html
    course.html
    search.html
    qa.html
    recommend.html
    profile.html
    teacher.html
  assets/
    css/
      base.css
      layout.css
      components.css
    js/
      api.js
      auth.js
      event.js
      qa.js
      search.js
      charts.js
      utils.js

## 3. 前端状态与数据流
- auth：token 存在 localStorage（或 sessionStorage）
- course_id：URL query 或 localStorage（统一约定）
- 页面加载 -> 拉取用户信息 / 课程信息 -> 渲染 -> 绑定事件 -> 埋点上报

## 4. API 调用约定
- Base URL：`/api/v1`
- Token：`Authorization: Bearer <token>`
- JSON：`Content-Type: application/json`
- 超时：建议 fetch 包装 10s timeout

## 5. 统一请求封装（api.js）
- apiGet(path, params)
- apiPost(path, body)
- apiUpload(path, file, extraFields)

要求：
- 统一处理 401：跳转 login
- 统一处理错误 toast：展示 `error.message` 或 `error.code`

## 6. 页面功能说明

### 6.1 search.html（知识检索）
- 输入关键词 -> GET `/kb/search`
- 展示结果列表（title/section/snippet）
- 点击条目：显示 chunk 详情 + “打开原文定位”
- 埋点：search、click_result、view_chunk

### 6.2 qa.html（智能问答）
- 输入问题 -> POST `/qa/ask`（或 WS `/qa/stream`）
- 展示答案 + citations（可展开原文片段）
- 反馈：点赞/踩 -> POST `/qa/feedback`
- 埋点：ask、answer_rendered、feedback

### 6.3 recommend.html（推荐）
- 根据 question 或 profile 拉取：
  - GET `/rec/by_question`
  - GET `/rec/by_profile`
- 展示前置知识/例题/易错点/下一步建议
- 埋点：view_recommend、click_recommend_item

### 6.4 profile.html（学情画像）
- GET `/analytics/student/{id}`
- 图表：活跃度趋势、薄弱知识点TopN、风险等级
- 埋点：view_profile

### 6.5 teacher.html（教师端）
- 上传资料 -> POST `/kb/upload`
- 入库任务 -> POST `/kb/ingest`
- 查看任务状态 -> GET `/kb/tasks/{task_id}`
- 班级面板 -> GET `/analytics/class/{course_id}`

## 7. 埋点事件规范（event.js）
统一事件格式：
{
  "user_id": "...",
  "course_id": "...",
  "event_type": "ask|search|view_doc|practice|collect|feedback|...",
  "payload": { ... },
  "ts": "ISO8601"
}

上报：
POST `/analytics/event`

最小事件集（必须实现）：
- search：{q, result_count}
- click_result：{chunk_id}
- ask：{question, mode: "rest|ws"}
- feedback：{qa_id, rating: 1|-1}
- view_profile：{}

## 8. UI/UX 约定
- citations 必须可展开显示 snippet
- 低置信度回答必须显著提示（例如“证据不足，需要澄清”）
- 所有列表需要 loading / empty / error 三态
