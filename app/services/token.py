import time
from loguru import logger
from app.config import get_settings
from app.utils.http import get_access_token_oapi


class TokenManager:
    """钉钉 access_token 管理：获取 + 缓存 + 自动刷新"""

    def __init__(self):
        self._token: str = ""
        self._expire_at: float = 0  # 过期时间戳

    @property
    def is_valid(self) -> bool:
        return bool(self._token) and time.time() < self._expire_at

    @property
    def expire_at_str(self) -> str:
        if not self._expire_at:
            return ""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._expire_at))

    async def refresh(self):
        """获取新的 access_token"""
        settings = get_settings()
        logger.info("正在刷新 access_token...")
        data = await get_access_token_oapi(settings.dingtalk_app_key, settings.dingtalk_app_secret)
        self._token = data["access_token"]
        # expires_in 是秒数，提前 600 秒（10分钟）视为过期
        expires_in = data.get("expires_in", 7200)
        self._expire_at = time.time() + expires_in - 600
        logger.info(f"access_token 刷新成功，有效期至 {self.expire_at_str}")

    async def get_token(self) -> str:
        """获取有效 token，过期则自动刷新"""
        if not self.is_valid:
            await self.refresh()
        return self._token


# 全局单例
token_manager = TokenManager()
