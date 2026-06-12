from datetime import datetime
from loguru import logger
from app.config import get_settings
from app.utils.http import dingtalk_post
from app.services.token import token_manager


class FolderManager:
    """知识库日期文件夹管理: 按需创建 + 内存缓存

    新版存储接口下，创建文件夹不会去重(同名会得到 xxx(1))，
    因此用内存缓存避免重复创建。进程重启后首次创建当前月份目录可能产生一个
    带后缀的副本——如需彻底去重，可申请 Storage.File.Read 权限改用列目录查找。
    """

    def __init__(self):
        # 缓存: { "2026-05": "folder_dentry_id" }
        self._cache: dict[str, str] = {}

    def _folder_name(self, date_str: str) -> str:
        """根据配置生成文件夹名: month -> "2026-05", day -> "2026-05-27" """
        settings = get_settings()
        if settings.folder_format == "day":
            return date_str
        # month 模式: "2026-05-27" -> "2026-05"
        return date_str[:7]

    async def _create_folder(self, space_id: str, root_parent_id: str, folder_name: str, token: str) -> str:
        """创建文件夹并返回其 dentryId

        POST /v1.0/storage/spaces/{spaceId}/dentries/{parentId}/folders
        """
        settings = get_settings()
        path = f"/v1.0/storage/spaces/{space_id}/dentries/{root_parent_id}/folders"
        body = {"name": folder_name}
        data = await dingtalk_post(path, token, body, params={"unionId": settings.dingtalk_admin_union_id})
        folder_id = data["dentry"]["id"]
        logger.info(f"创建文件夹成功: {folder_name} -> dentryId={folder_id}")
        return folder_id

    async def ensure_folder(self, space_id: str, root_parent_id: str, date_str: str, token: str) -> tuple[str, str]:
        """确保日期文件夹存在，返回 (文件夹名, 文件夹dentryId)。

        需要 space_id 和 root_parent_id(根目录的 dentryId)——均由上传到根目录后的
        commit 响应提供(dentry.spaceId / dentry.parentId)。
        """
        folder_name = self._folder_name(date_str)

        # 查缓存
        if folder_name in self._cache:
            return folder_name, self._cache[folder_name]

        folder_id = await self._create_folder(space_id, root_parent_id, folder_name, token)
        self._cache[folder_name] = folder_id
        logger.info(f"日期文件夹就绪: {folder_name} -> {folder_id}")
        return folder_name, folder_id


# 全局单例
folder_manager = FolderManager()
