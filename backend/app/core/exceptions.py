from fastapi import HTTPException
from typing import Any, Dict, Optional


class BaseAPIException(HTTPException):
    """基础API异常类"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        
        detail = {
            "error": {
                "code": error_code,
                "message": message,
                "details": self.details
            }
        }
        super().__init__(status_code=status_code, detail=detail)


# 认证相关异常
class AuthInvalidException(BaseAPIException):
    def __init__(self, message: str = "认证无效"):
        super().__init__(401, "AUTH_INVALID", message)


class PermissionDeniedException(BaseAPIException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(403, "PERMISSION_DENIED", message)


# 知识库相关异常
class KBUploadFailedException(BaseAPIException):
    def __init__(self, message: str = "文件上传失败", details: Dict = None):
        super().__init__(400, "KB_UPLOAD_FAILED", message, details)


class KBParseFailedException(BaseAPIException):
    def __init__(self, message: str = "文档解析失败", details: Dict = None):
        super().__init__(400, "KB_PARSE_FAILED", message, details)


class KBIngestFailedException(BaseAPIException):
    def __init__(self, message: str = "文档入库失败", details: Dict = None):
        super().__init__(500, "KB_INGEST_FAILED", message, details)


# 向量数据库异常
class VectorDBException(BaseAPIException):
    def __init__(self, message: str = "向量数据库错误", details: Dict = None):
        super().__init__(500, "VECTORDB_ERROR", message, details)


# LLM相关异常
class LLMException(BaseAPIException):
    def __init__(self, message: str = "LLM调用失败", details: Dict = None):
        super().__init__(500, "LLM_ERROR", message, details)


# QA相关异常
class QALowConfidenceException(BaseAPIException):
    def __init__(self, message: str = "置信度过低，无法提供可靠答案", details: Dict = None):
        super().__init__(200, "QA_LOW_CONFIDENCE", message, details)


# 分析相关异常
class AnalyticsException(BaseAPIException):
    def __init__(self, message: str = "分析服务错误", details: Dict = None):
        super().__init__(500, "ANALYTICS_ERROR", message, details)


# 文件相关异常
class FileNotSupportedException(BaseAPIException):
    def __init__(self, file_type: str):
        message = f"不支持的文件类型: {file_type}"
        super().__init__(400, "FILE_NOT_SUPPORTED", message)


class FileTooLargeException(BaseAPIException):
    def __init__(self, size: int, max_size: int):
        message = f"文件过大: {size} bytes, 最大允许: {max_size} bytes"
        super().__init__(400, "FILE_TOO_LARGE", message)


# 任务相关异常
class TaskNotFoundException(BaseAPIException):
    def __init__(self, task_id: str):
        message = f"任务不存在: {task_id}"
        super().__init__(404, "TASK_NOT_FOUND", message)


class TaskFailedException(BaseAPIException):
    def __init__(self, task_id: str, error: str):
        message = f"任务执行失败: {task_id}"
        details = {"task_id": task_id, "error": error}
        super().__init__(500, "TASK_FAILED", message, details)