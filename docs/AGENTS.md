<!-- docs/04-AGENTS.md -->
# 智能体开发文档（RAG / 推荐 / 学情）

## 1. 问答助手智能体（QA Agent）
### 1.1 目标
- 基于课程知识库回答问题
- 必须提供引用证据（citations）
- 证据不足要拒答/澄清

### 1.2 RAG 链路
1) normalize(question)
2) retrieve(course_id, question_embedding, top_k=12)
3) (optional) rerank(question, candidates, top_n=6)
4) build_prompt(question, evidence_chunks)
5) llm_generate(prompt, stream=True)
6) compute_confidence(evidence_scores, answer_signals)
7) return(answer, citations, confidence, followups)

### 1.3 Prompt 模板约束（必须）
- 只允许使用 evidence 中的信息回答
- 输出结构固定：
  - 结论
  - 解释/推导
  - 引用（按 [1][2] 标号对应 citations）
- 不得编造；若 evidence 不足必须说明缺少什么

### 1.4 置信度计算（工程版）
建议组合：
- avg_top_scores：检索/重排得分均值
- coverage：引用 chunk 数量与多样性
- refusal_flag：模型是否触发“证据不足”模板

最终：
confidence = clamp(0..1, w1*score + w2*coverage - w3*refusal)

阈值：
- confidence < 0.45：强制澄清/拒答
- 0.45~0.65：提示“不确定”，建议阅读章节
- >0.65：正常回答

## 2. 知识点推荐智能体（Rec Agent）
### 2.1 输入
- question 或 user_profile（薄弱知识点列表）

### 2.2 输出结构
{
  "prerequisites": [kp...],
  "examples": [item...],
  "pitfalls": [item...],
  "next_steps": [item...]
}

### 2.3 规则优先级
- 如果来自错题/重复问：优先 prerequisites + pitfalls
- 如果来自章节学习进度：优先 next_steps + examples

### 2.4 知识点映射策略
- 基于 chunk -> kp（chunk 元数据或离线映射表）
- 或在线：对 question/证据 chunks 做 kp 分类（可选，后续迭代）

## 3. 学情分析智能体（Analytics Agent）
### 3.1 事件输入
- events：search/ask/view_doc/practice/feedback/collect
- qa_logs：confidence、citations、满意度

### 3.2 指标（最小集）
- active_7d：近7天事件数/学习时长（若有）
- weak_kp_topn：由重复问/低置信/错题聚合得到
- risk_level：
  - low：正常
  - medium：存在持续卡点或不活跃趋势
  - high：长时间不活跃 + 多知识点卡点/错题率高

### 3.3 预警规则（默认）
- 7 天内连续 3 天无有效学习事件 -> medium
- 同一 kp 7 天内重复提问 >= 4 且 avg_conf < 0.55 -> medium
- 2 个及以上 kp 同时触发卡点规则 -> high

### 3.4 输出
- student_profile：指标 + 解释 + 建议学习路径
- class_dashboard：聚合薄弱章节/知识点分布 + 预警名单
