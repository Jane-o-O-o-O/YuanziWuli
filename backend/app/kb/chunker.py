import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """文本块"""
    index: int
    text: str
    metadata: Dict[str, Any]
    start_offset: int
    end_offset: int


class TextChunker:
    """文本分块器"""
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP
    
    def chunk_document(self, parsed_doc: Dict[str, Any]) -> List[TextChunk]:
        """对解析后的文档进行分块"""
        content = parsed_doc.get("content", [])
        doc_type = parsed_doc.get("metadata", {}).get("type", "unknown")
        
        if doc_type == "pdf":
            return self._chunk_pdf_content(content)
        elif doc_type in ["docx", "txt"]:
            return self._chunk_paragraph_content(content)
        elif doc_type == "pptx":
            return self._chunk_slide_content(content)
        elif doc_type == "markdown":
            return self._chunk_markdown_content(content)
        else:
            # 默认按原始文本分块
            raw_text = parsed_doc.get("raw_text", "")
            return self._chunk_raw_text(raw_text)
    
    def _chunk_pdf_content(self, content: List[Dict]) -> List[TextChunk]:
        """PDF内容分块"""
        chunks = []
        chunk_index = 0
        
        for page_info in content:
            page_text = page_info["text"]
            page_num = page_info["page"]
            section = page_info["section"]
            
            # 如果页面文本较短，直接作为一个块
            if len(page_text) <= self.chunk_size:
                chunks.append(TextChunk(
                    index=chunk_index,
                    text=page_text,
                    metadata={
                        "section": section,
                        "page": page_num,
                        "chunk_type": "page"
                    },
                    start_offset=0,
                    end_offset=len(page_text)
                ))
                chunk_index += 1
            else:
                # 页面文本较长，需要进一步分块
                page_chunks = self._split_text_with_overlap(page_text)
                for i, chunk_text in enumerate(page_chunks):
                    chunks.append(TextChunk(
                        index=chunk_index,
                        text=chunk_text,
                        metadata={
                            "section": section,
                            "page": page_num,
                            "chunk_type": "page_part",
                            "part": i + 1
                        },
                        start_offset=0,  # 简化处理
                        end_offset=len(chunk_text)
                    ))
                    chunk_index += 1
        
        return chunks
    
    def _chunk_paragraph_content(self, content: List[Dict]) -> List[TextChunk]:
        """段落内容分块"""
        chunks = []
        chunk_index = 0
        current_chunk = ""
        current_section = ""
        current_metadata = {}
        
        for para_info in content:
            para_text = para_info["text"]
            section = para_info.get("section", "")
            
            # 如果是新的章节，且当前块不为空，先保存当前块
            if section != current_section and current_chunk:
                chunks.append(TextChunk(
                    index=chunk_index,
                    text=current_chunk.strip(),
                    metadata=current_metadata,
                    start_offset=0,
                    end_offset=len(current_chunk)
                ))
                chunk_index += 1
                current_chunk = ""
            
            current_section = section
            current_metadata = {
                "section": section,
                "paragraph": para_info.get("paragraph", 0),
                "chunk_type": "paragraph"
            }
            
            # 检查添加当前段落后是否超过块大小
            if len(current_chunk + "\n" + para_text) > self.chunk_size:
                # 如果当前块不为空，先保存
                if current_chunk:
                    chunks.append(TextChunk(
                        index=chunk_index,
                        text=current_chunk.strip(),
                        metadata=current_metadata,
                        start_offset=0,
                        end_offset=len(current_chunk)
                    ))
                    chunk_index += 1
                
                # 如果单个段落就很长，需要分割
                if len(para_text) > self.chunk_size:
                    para_chunks = self._split_text_with_overlap(para_text)
                    for i, chunk_text in enumerate(para_chunks):
                        chunks.append(TextChunk(
                            index=chunk_index,
                            text=chunk_text,
                            metadata={
                                **current_metadata,
                                "part": i + 1
                            },
                            start_offset=0,
                            end_offset=len(chunk_text)
                        ))
                        chunk_index += 1
                    current_chunk = ""
                else:
                    current_chunk = para_text
            else:
                # 添加到当前块
                if current_chunk:
                    current_chunk += "\n" + para_text
                else:
                    current_chunk = para_text
        
        # 保存最后的块
        if current_chunk:
            chunks.append(TextChunk(
                index=chunk_index,
                text=current_chunk.strip(),
                metadata=current_metadata,
                start_offset=0,
                end_offset=len(current_chunk)
            ))
        
        return chunks
    
    def _chunk_slide_content(self, content: List[Dict]) -> List[TextChunk]:
        """幻灯片内容分块"""
        chunks = []
        
        for i, slide_info in enumerate(content):
            slide_text = slide_info["text"]
            slide_num = slide_info["slide"]
            section = slide_info["section"]
            
            # 每张幻灯片作为一个块（除非文本过长）
            if len(slide_text) <= self.chunk_size:
                chunks.append(TextChunk(
                    index=i,
                    text=slide_text,
                    metadata={
                        "section": section,
                        "slide": slide_num,
                        "chunk_type": "slide"
                    },
                    start_offset=0,
                    end_offset=len(slide_text)
                ))
            else:
                # 幻灯片文本过长，分割
                slide_chunks = self._split_text_with_overlap(slide_text)
                for j, chunk_text in enumerate(slide_chunks):
                    chunks.append(TextChunk(
                        index=len(chunks),
                        text=chunk_text,
                        metadata={
                            "section": section,
                            "slide": slide_num,
                            "chunk_type": "slide_part",
                            "part": j + 1
                        },
                        start_offset=0,
                        end_offset=len(chunk_text)
                    ))
        
        return chunks
    
    def _chunk_markdown_content(self, content: List[Dict]) -> List[TextChunk]:
        """Markdown内容分块"""
        chunks = []
        chunk_index = 0
        
        for section_info in content:
            section_text = section_info["text"]
            section_name = section_info["section"]
            
            if len(section_text) <= self.chunk_size:
                chunks.append(TextChunk(
                    index=chunk_index,
                    text=section_text,
                    metadata={
                        "section": section_name,
                        "chunk_type": "section"
                    },
                    start_offset=0,
                    end_offset=len(section_text)
                ))
                chunk_index += 1
            else:
                # 章节文本过长，分割
                section_chunks = self._split_text_with_overlap(section_text)
                for i, chunk_text in enumerate(section_chunks):
                    chunks.append(TextChunk(
                        index=chunk_index,
                        text=chunk_text,
                        metadata={
                            "section": section_name,
                            "chunk_type": "section_part",
                            "part": i + 1
                        },
                        start_offset=0,
                        end_offset=len(chunk_text)
                    ))
                    chunk_index += 1
        
        return chunks
    
    def _chunk_raw_text(self, text: str) -> List[TextChunk]:
        """原始文本分块"""
        chunks = []
        text_chunks = self._split_text_with_overlap(text)
        
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(TextChunk(
                index=i,
                text=chunk_text,
                metadata={
                    "section": f"文本块{i+1}",
                    "chunk_type": "raw"
                },
                start_offset=0,
                end_offset=len(chunk_text)
            ))
        
        return chunks
    
    def _split_text_with_overlap(self, text: str) -> List[str]:
        """带重叠的文本分割"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 寻找句号、问号、感叹号等句子结束符
                sentence_end = self._find_sentence_boundary(text, start, end)
                if sentence_end > start:
                    end = sentence_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 计算下一个块的起始位置（考虑重叠）
            if end >= len(text):
                break
            
            start = max(start + 1, end - self.overlap)
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """寻找句子边界"""
        # 在preferred_end附近寻找句子结束符
        search_start = max(start, preferred_end - 100)
        search_end = min(len(text), preferred_end + 100)
        
        # 句子结束符的优先级
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n\n']
        
        best_pos = preferred_end
        for ending in sentence_endings:
            pos = text.rfind(ending, search_start, search_end)
            if pos > start and abs(pos - preferred_end) < abs(best_pos - preferred_end):
                best_pos = pos + len(ending)
        
        return best_pos