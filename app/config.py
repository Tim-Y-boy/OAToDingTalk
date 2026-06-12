from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 钉钉应用凭证
    dingtalk_app_key: str
    dingtalk_app_secret: str

    # 钉钉知识库
    dingtalk_space_id: str = ""
    dingtalk_root_dentry_uuid: str = ""
    dingtalk_admin_union_id: str = ""

    # 文件夹命名: month 或 day
    folder_format: str = "month"

    # OA 鉴权
    api_key: str = ""

    # 服务端口
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
