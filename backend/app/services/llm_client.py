import openai
import httpx
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import LLMException

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Embedding结果"""
    embedding: List[float]
    model: str
    usage: Dict[str, int]


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


@dataclass
class RerankResult:
    """重排序结果"""
    index: int
    score: float
    document: str


class SiliconFlowClient:
    """硅基流动客户端"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL
        )
        self.http_client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={"Authorization": f"Bearer {settings.SILICONFLOW_API_KEY}"}
        )
    
    async def get_embedding(self, text: str, model: str = None) -> EmbeddingResult:
        """获取文本向量"""
        if model is None:
            model = settings.EMBEDDING_MODEL
        
        try:
            # 截断过长的文本（512 tokens ≈ 1024 中文字符）
            # 更保守的限制：400 字符（约 200 tokens）
            max_chars = 400
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.warning(f"文本过长，已截断到 {max_chars} 字符")
            
            response = self.client.embeddings.create(
                model=model,
                input=[text]
            )
            
            return EmbeddingResult(
                embedding=response.data[0].embedding,
                model=model,
                usage=response.usage.model_dump() if response.usage else {}
            )
            
        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            raise LLMException(f"向量化失败: {e}")
    
    async def get_embeddings_batch(self, texts: List[str], model: str = None) -> List[EmbeddingResult]:
        """批量获取文本向量"""
        if model is None:
            model = settings.EMBEDDING_MODEL
        
        try:
            # 截断过长的文本（512 tokens ≈ 1024 中文字符）
            # 更保守的限制：400 字符（约 200 tokens）
            max_chars = 400
            truncated_texts = []
            for text in texts:
                if len(text) > max_chars:
                    truncated_text = text[:max_chars]
                    logger.warning(f"文本过长，已截断: {len(text)} -> {max_chars} 字符")
                    truncated_texts.append(truncated_text)
                else:
                    truncated_texts.append(text)
            
            # 分批处理，避免单次请求过大
            batch_size = min(settings.EMBEDDING_BATCH_SIZE, 16)  # 限制批量大小
            results = []
            
            for i in range(0, len(truncated_texts), batch_size):
                batch_texts = truncated_texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    model=model,
                    input=batch_texts
                )
                
                for j, data in enumerate(response.data):
                    results.append(EmbeddingResult(
                        embedding=data.embedding,
                        model=model,
                        usage=response.usage.model_dump() if response.usage else {}
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"批量获取向量失败: {e}")
            raise LLMException(f"批量向量化失败: {e}")
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> ChatResponse:
        """聊天补全"""
        if model is None:
            model = settings.LLM_MODEL
        
        try:
            message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            if stream:
                return await self._chat_completion_stream(message_dicts, model, temperature, max_tokens)
            else:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=message_dicts,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return ChatResponse(
                    content=response.choices[0].message.content,
                    model=model,
                    usage=response.usage.model_dump() if response.usage else {},
                    finish_reason=response.choices[0].finish_reason
                )
                
        except Exception as e:
            logger.error(f"聊天补全失败: {e}")
            raise LLMException(f"LLM调用失败: {e}")
    
    async def chat_completion_stream(
        self,
        messages: List[ChatMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        if model is None:
            model = settings.LLM_MODEL
        
        try:
            message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            stream = self.client.chat.completions.create(
                model=model,
                messages=message_dicts,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"流式聊天补全失败: {e}")
            raise LLMException(f"流式LLM调用失败: {e}")
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        model: str = None,
        top_n: int = None
    ) -> List[RerankResult]:
        """重排序"""
        if model is None:
            model = settings.RERANK_MODEL
        if top_n is None:
            top_n = settings.RERANK_TOP_N
        
        try:
            response = await self.http_client.post(
                f"{settings.SILICONFLOW_BASE_URL}/rerank",
                json={
                    "model": model,
                    "query": query,
                    "documents": documents,
                    "top_n": min(top_n, len(documents))
                }
            )
            
            if response.status_code != 200:
                trace_id = response.headers.get("x-siliconcloud-trace-id")
                try:
                    body = response.json()
                except Exception:
                    body = response.text
                raise Exception(f"重排序API调用失败: {response.status_code}, trace_id={trace_id}, body={body}")
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append(RerankResult(
                    index=item["index"],
                    score=item["relevance_score"],
                    document=documents[item["index"]]
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            raise LLMException(f"重排序失败: {e}")
    
    async def close(self):
        """关闭客户端"""
        await self.http_client.aclose()


# 全局客户端实例
llm_client = SiliconFlowClient()