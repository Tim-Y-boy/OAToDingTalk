from pydantic import BaseModel, HttpUrl
from typing import Optional


# ---- 请求模型 ----

class UploadByUrlRequest(BaseModel):
    file_url: str
    file_name: str
    date: Optional[str] = None  # "2026-05-27", 默认当天


# ---- 响应模型 ----

class UploadResponse(BaseModel):
    success: bool
    dentry_uuid: str = ""
    folder: str = ""
    file_name: str = ""
    message: str = ""


class HealthResponse(BaseModel):
    status: str
    token_valid: bool
    token_expire_at: str = ""
