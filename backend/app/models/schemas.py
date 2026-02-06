from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# 基础响应模型
class BaseResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"


class ErrorResponse(BaseModel):
    error: Dict[str, Any]


# 用户相关模型
class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.STUDENT


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# 课程相关模型
class CourseCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class CourseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# 文档相关模型
class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentResponse(BaseModel):
    id: int
    course_id: int
    file_name: str
    file_type: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    document_id: int
    status: str


# 知识库相关模型
class ChunkPolicy(BaseModel):
    max_chars: int = 800
    overlap: int = 120


class IngestRequest(BaseModel):
    document_id: int
    chunk_policy: Optional[ChunkPolicy] = None


class IngestResponse(BaseModel):
    task_id: str
    status: str


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    error: Optional[str] = None


class SearchHit(BaseModel):
    chunk_id: int
    score: float
    document_id: int
    meta: Dict[str, Any]
    snippet: str


class SearchResponse(BaseModel):
    hits: List[SearchHit]


# QA相关模型
class QARequest(BaseModel):
    course_id: int
    question: str = Field(..., max_length=2000)
    top_k: int = 12


class Citation(BaseModel):
    chunk_id: int
    document_id: int
    section: Optional[str]
    snippet: str


class QAResponse(BaseModel):
    qa_id: Optional[int] = None
    answer: str
    confidence: float
    citations: List[Citation]
    followups: List[str] = []


class FeedbackRequest(BaseModel):
    qa_id: int
    rating: int = Field(..., ge=-1, le=1)  # 1=like, -1=dislike


# WebSocket消息模型
class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any]


class WSQARequest(BaseModel):
    course_id: int
    question: str


class WSQADelta(BaseModel):
    type: str = "delta"
    text: str


class WSQAFinal(BaseModel):
    type: str = "final"
    qa_id: int
    confidence: float
    citations: List[Citation]


# 推荐相关模型
class RecommendationItem(BaseModel):
    kp: str
    description: str
    actions: List[str]


class RecommendationResponse(BaseModel):
    prerequisites: List[RecommendationItem] = []
    examples: List[RecommendationItem] = []
    pitfalls: List[RecommendationItem] = []
    next_steps: List[RecommendationItem] = []


class LearningPlan(BaseModel):
    kp: str
    actions: List[str]


class ProfileRecommendationResponse(BaseModel):
    plan: List[LearningPlan]


# 分析相关模型
class EventRequest(BaseModel):
    user_id: int
    course_id: int
    event_type: str
    payload: Dict[str, Any] = {}
    ts: Optional[datetime] = None


class WeakKnowledgePoint(BaseModel):
    kp: str
    score: float


class StudentProfile(BaseModel):
    active_7d: int
    weak_kp: List[WeakKnowledgePoint]
    risk_level: str
    reasons: List[str]
    suggestions: List[str]


class WeakKPDistribution(BaseModel):
    kp: str
    count: int


class ClassAlert(BaseModel):
    user_id: int
    level: str
    reason: str


class ClassDashboard(BaseModel):
    weak_kp_dist: List[WeakKPDistribution]
    alerts: List[ClassAlert]