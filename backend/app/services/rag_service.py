import logging
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import QALowConfidenceException, LLMException
from app.models.orm import QALog, Chunk, Document
from app.models.schemas import Citation
from app.services.llm_client import llm_client, ChatMessage
from app.services.kb_service import kb_service

logger = logging.getLogger(__name__)


class RAGService:
    """RAG服务"""
    
    def __init__(self):
        self.confidence_threshold = settings.CONFIDENCE_THRESHOLD
    
    async def ask_question(
        self,
        db: Session,
        user_id: int,
        course_id: int,
        question: str,
        top_k: int = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """问答"""
        if top_k is None:
            top_k = settings.TOP_K
        
        try:
            # 1. 问题标准化
            normalized_question = self._normalize_question(question)
            
            # 2. 向量检索
            search_results = await kb_service.search_knowledge(
                course_id=course_id,
                query=normalized_question,
                top_k=top_k
            )
            
            if not search_results:
                return self._create_no_evidence_response(question)
            
            # 3. 重排序（可选）
            if len(search_results) > settings.RERANK_TOP_N:
                reranked_results = await self._rerank_results(normalized_question, search_results)
                final_results = reranked_results[:settings.RERANK_TOP_N]
            else:
                final_results = search_results
            
            # 4. 获取完整文本块信息
            chunk_details = await self._get_chunk_details(db, final_results)
            
            # 5. 构建提示词
            prompt = self._build_rag_prompt(normalized_question, chunk_details)
            
            # 6. LLM生成答案
            if stream:
                return await self._generate_answer_stream(
                    db, user_id, course_id, question, prompt, chunk_details
                )
            else:
                return await self._generate_answer(
                    db, user_id, course_id, question, prompt, chunk_details
                )
                
        except Exception as e:
            logger.error(f"问答失败: {e}")
            raise LLMException(f"问答服务失败: {e}")
    
    def _normalize_question(self, question: str) -> str:
        """问题标准化"""
        # 去除多余空格
        question = re.sub(r'\s+', ' ', question.strip())
        
        # 确保问题以问号结尾
        if not question.endswith(('?', '？')):
            question += '？'
        
        return question
    
    async def _rerank_results(self, question: str, results: List[Dict]) -> List[Dict]:
        """重排序检索结果"""
        try:
            documents = [result["snippet"] for result in results]
            rerank_results = await llm_client.rerank(question, documents, top_n=settings.RERANK_TOP_N)
            
            # 根据重排序结果重新排列
            reranked = []
            for rerank_result in rerank_results:
                original_result = results[rerank_result.index].copy()
                original_result["rerank_score"] = rerank_result.score
                reranked.append(original_result)
            
            return reranked
            
        except Exception as e:
            logger.warning(f"重排序失败，使用原始结果: {e}")
            return results
    
    async def _get_chunk_details(self, db: Session, results: List[Dict]) -> List[Dict]:
        """获取文本块详细信息"""
        chunk_ids = [result["chunk_id"] for result in results]
        
        chunks = db.query(Chunk, Document).join(
            Document, Chunk.document_id == Document.id
        ).filter(Chunk.id.in_(chunk_ids)).all()
        
        chunk_map = {chunk.id: (chunk, doc) for chunk, doc in chunks}
        
        detailed_results = []
        for result in results:
            chunk_id = result["chunk_id"]
            if chunk_id in chunk_map:
                chunk, document = chunk_map[chunk_id]
                detailed_results.append({
                    **result,
                    "chunk": chunk,
                    "document": document,
                    "full_text": chunk.chunk_text
                })
        
        return detailed_results
    
    def _build_rag_prompt(self, question: str, chunk_details: List[Dict]) -> str:
        """构建RAG提示词"""
        # 构建证据文本
        evidence_parts = []
        for i, detail in enumerate(chunk_details, 1):
            chunk = detail["chunk"]
            document = detail["document"]
            section = chunk.meta_json.get("section", "未知章节")
            
            evidence_parts.append(
                f"[{i}] 来源：《{document.file_name}》- {section}\n"
                f"内容：{chunk.chunk_text}\n"
            )
        
        evidence_text = "\n".join(evidence_parts)
        
        # 构建完整提示词
        prompt = f"""你是一个原子物理学专家，请基于以下证据回答问题。

证据材料：
{evidence_text}

问题：{question}

回答要求：
1. 基于上述证据中的信息回答问题
2. 回答要准确、完整、有逻辑性
3. 使用专业但易懂的语言
4. 不要出现下面的回答，⚠️ 证据不足，以下回答仅供参考：
5. 我们的信息肯定是准确的

请按以下格式回答：
**结论：**
[简明扼要的答案]

**详细解释：**
[详细的推导和解释过程]

回答："""
        
        return prompt
    
    async def _generate_answer(
        self,
        db: Session,
        user_id: int,
        course_id: int,
        question: str,
        prompt: str,
        chunk_details: List[Dict]
    ) -> Dict[str, Any]:
        """生成答案"""
        try:
            # 调用LLM
            messages = [
                ChatMessage(role="system", content="你是一个专业的原子物理学教学助手。"),
                ChatMessage(role="user", content=prompt)
            ]
            
            response = await llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            answer = response.content
            
            # 计算置信度
            confidence = self._calculate_confidence(chunk_details, answer)
            
            # 提取引用
            citations = self._extract_citations(chunk_details, answer)
            
            # 生成后续问题建议
            followups = self._generate_followups(question, answer)
            
            # 检查置信度
            if confidence < self.confidence_threshold:
                return self._create_low_confidence_response(question, answer, confidence, citations)
            
            # 保存问答日志
            qa_log = QALog(
                user_id=user_id,
                course_id=course_id,
                question=question,
                answer=answer,
                citations_json=[citation.dict() for citation in citations],
                confidence=confidence
            )
            db.add(qa_log)
            db.commit()
            db.refresh(qa_log)
            
            return {
                "qa_id": qa_log.id,
                "answer": answer,
                "confidence": confidence,
                "citations": citations,
                "followups": followups
            }
            
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            raise LLMException(f"答案生成失败: {e}")
    
    async def _generate_answer_stream(
        self,
        db: Session,
        user_id: int,
        course_id: int,
        question: str,
        prompt: str,
        chunk_details: List[Dict]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式生成答案"""
        try:
            messages = [
                ChatMessage(role="system", content="你是一个专业的原子物理学教学助手。"),
                ChatMessage(role="user", content=prompt)
            ]
            
            full_answer = ""
            
            # 流式生成
            async for chunk in llm_client.chat_completion_stream(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            ):
                full_answer += chunk
                yield {"type": "delta", "text": chunk}
            
            # 计算置信度和引用
            confidence = self._calculate_confidence(chunk_details, full_answer)
            citations = self._extract_citations(chunk_details, full_answer)
            
            # 保存问答日志
            qa_log = QALog(
                user_id=user_id,
                course_id=course_id,
                question=question,
                answer=full_answer,
                citations_json=[citation.dict() for citation in citations],
                confidence=confidence
            )
            db.add(qa_log)
            db.commit()
            db.refresh(qa_log)
            
            # 发送最终结果
            yield {
                "type": "final",
                "qa_id": qa_log.id,
                "confidence": confidence,
                "citations": citations
            }
            
        except Exception as e:
            logger.error(f"流式答案生成失败: {e}")
            yield {"type": "error", "message": str(e)}
    
    def _calculate_confidence(self, chunk_details: List[Dict], answer: str) -> float:
        """计算置信度"""
        if not chunk_details:
            return 0.0
        
        # 基础分数：检索分数的平均值
        avg_score = sum(detail.get("score", 0) for detail in chunk_details) / len(chunk_details)
        
        # 覆盖度：引用的证据数量
        cited_count = len(re.findall(r'\[(\d+)\]', answer))
        coverage = min(cited_count / len(chunk_details), 1.0)
        
        # 拒答检测：是否包含"不足"、"无法"等词汇
        refusal_keywords = ['证据不足', '无法确定', '不能确定', '信息不够', '需要更多']
        refusal_flag = any(keyword in answer for keyword in refusal_keywords)
        
        # 综合计算
        confidence = 0.4 * avg_score + 0.4 * coverage + 0.2
        
        if refusal_flag:
            confidence *= 0.5
        
        return max(0.0, min(1.0, confidence))
    
    def _extract_citations(self, chunk_details: List[Dict], answer: str) -> List[Citation]:
        """提取引用"""
        citations = []
        citation_numbers = re.findall(r'\[(\d+)\]', answer)
        
        for num_str in set(citation_numbers):
            try:
                num = int(num_str)
                if 1 <= num <= len(chunk_details):
                    detail = chunk_details[num - 1]
                    chunk = detail["chunk"]
                    document = detail["document"]
                    
                    citations.append(Citation(
                        chunk_id=chunk.id,
                        document_id=document.id,
                        section=chunk.meta_json.get("section"),
                        snippet=chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text
                    ))
            except (ValueError, IndexError):
                continue
        
        return citations
    
    def _generate_followups(self, question: str, answer: str) -> List[str]:
        """生成后续问题建议"""
        # 简单的后续问题生成逻辑
        followups = []
        
        # 基于问题类型生成
        if "什么是" in question or "定义" in question:
            followups.append("这个概念有哪些应用？")
            followups.append("相关的实验有哪些？")
        elif "如何" in question or "怎样" in question:
            followups.append("这种方法的原理是什么？")
            followups.append("有什么注意事项？")
        elif "为什么" in question:
            followups.append("这个现象的应用有哪些？")
            followups.append("相关的理论发展历史如何？")
        
        # 基于答案内容生成
        if "实验" in answer:
            followups.append("这个实验的具体步骤是什么？")
        if "公式" in answer or "方程" in answer:
            followups.append("这个公式如何推导？")
        if "应用" in answer:
            followups.append("还有哪些实际应用？")
        
        return followups[:3]  # 最多返回3个建议
    
    def _create_no_evidence_response(self, question: str) -> Dict[str, Any]:
        """创建无证据响应"""
        return {
            "qa_id": None,
            "answer": f"抱歉，我在知识库中没有找到与问题「{question}」相关的信息。请尝试：\n1. 使用更具体的关键词\n2. 检查问题的表述是否准确\n3. 确认问题是否属于原子物理学范围",
            "confidence": 0.0,
            "citations": [],
            "followups": ["什么是原子结构？", "波粒二象性是什么？", "量子数有哪些？"]
        }
    
    def _create_low_confidence_response(
        self,
        question: str,
        answer: str,
        confidence: float,
        citations: List[Citation]
    ) -> Dict[str, Any]:
        """创建低置信度响应"""
        warning_answer = f"{answer}"
        
        return {
            "qa_id": None,
            "answer": warning_answer,
            "confidence": confidence,
            "citations": citations,
            "followups": ["需要查看哪些相关资料？", "这个问题的关键概念是什么？"]
        }
    
    async def add_feedback(self, db: Session, qa_id: int, rating: int):
        """添加反馈"""
        qa_log = db.query(QALog).filter(QALog.id == qa_id).first()
        if qa_log:
            qa_log.rating = rating
            db.commit()
            logger.info(f"问答反馈已保存: qa_id={qa_id}, rating={rating}")


# 全局服务实例
rag_service = RAGService()