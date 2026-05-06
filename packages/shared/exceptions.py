from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """统一错误码。"""

    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"

    FEISHU_ERROR = "FEISHU_ERROR"
    FEISHU_API_ERROR = "FEISHU_API_ERROR"
    FEISHU_TOKEN_ERROR = "FEISHU_TOKEN_ERROR"
    FEISHU_EVENT_ERROR = "FEISHU_EVENT_ERROR"
    FEISHU_MESSAGE_ERROR = "FEISHU_MESSAGE_ERROR"

    TASK_ERROR = "TASK_ERROR"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_STATUS_ERROR = "TASK_STATUS_ERROR"

    PLANNER_ERROR = "PLANNER_ERROR"
    AGENT_ERROR = "AGENT_ERROR"


class AppException(Exception):
    """项目基础异常。"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        detail: Any | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "message": self.message,
            "detail": self.detail,
        }


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", detail: Any | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.BAD_REQUEST,
            status_code=400,
            detail=detail,
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", detail: Any | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.UNAUTHORIZED,
            status_code=401,
            detail=detail,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden", detail: Any | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            status_code=403,
            detail=detail,
        )


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", detail: Any | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            detail=detail,
        )


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict", detail: Any | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=409,
            detail=detail,
        )


class FeishuException(AppException):
    """飞书相关基础异常。"""

    def __init__(
        self,
        message: str = "Feishu error",
        detail: Any | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FEISHU_ERROR,
            status_code=status_code,
            detail=detail,
        )


class FeishuApiException(AppException):
    """飞书开放平台 API 调用异常。

    这个类是为了匹配 client.py 里的 import：
    from packages.shared.exceptions import FeishuApiError
    """

    def __init__(
        self,
        message: str = "Feishu API request failed",
        detail: Any | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FEISHU_API_ERROR,
            status_code=status_code,
            detail=detail,
        )


class FeishuTokenException(AppException):
    """飞书 tenant_access_token 获取或刷新失败。"""

    def __init__(
        self,
        message: str = "Failed to get Feishu tenant access token",
        detail: Any | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FEISHU_TOKEN_ERROR,
            status_code=500,
            detail=detail,
        )


class FeishuEventException(AppException):
    """飞书事件解析、验签、标准化失败。"""

    def __init__(
        self,
        message: str = "Failed to handle Feishu event",
        detail: Any | None = None,
        status_code: int = 400,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FEISHU_EVENT_ERROR,
            status_code=status_code,
            detail=detail,
        )


class FeishuMessageException(AppException):
    """飞书消息发送、回复、读取失败。"""

    def __init__(
        self,
        message: str = "Failed to handle Feishu message",
        detail: Any | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FEISHU_MESSAGE_ERROR,
            status_code=status_code,
            detail=detail,
        )


class TaskException(AppException):
    """任务相关基础异常。"""

    def __init__(
        self,
        message: str = "Task error",
        detail: Any | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.TASK_ERROR,
            status_code=status_code,
            detail=detail,
        )


class TaskNotFoundException(AppException):
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            code=ErrorCode.TASK_NOT_FOUND,
            status_code=404,
            detail={"task_id": task_id},
        )


class TaskStatusException(AppException):
    """任务状态流转异常。"""

    def __init__(
        self,
        message: str = "Invalid task status transition",
        detail: Any | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.TASK_STATUS_ERROR,
            status_code=400,
            detail=detail,
        )


class PlannerException(AppException):
    """Planner 规划异常。"""

    def __init__(
        self,
        message: str = "Planner error",
        detail: Any | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.PLANNER_ERROR,
            status_code=status_code,
            detail=detail,
        )


class AgentException(AppException):
    """Agent 执行异常。"""

    def __init__(
        self,
        message: str = "Agent execution error",
        detail: Any | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AGENT_ERROR,
            status_code=status_code,
            detail=detail,
        )
