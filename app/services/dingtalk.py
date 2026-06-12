import os
from loguru import logger
from app.utils.http import dingtalk_post, upload_to_oss


async def get_upload_info(parent_dentry_uuid: str, union_id: str, token: str, file_name: str) -> dict:
    """步骤1: 获取文件上传信息（uploadKey + OSS地址 + 签名）

    新版存储接口：POST /v2.0/storage/spaces/files/{parentDentryUuid}/uploadInfos/query
    注：unionId 放在请求体里。
    """
    path = f"/v2.0/storage/spaces/files/{parent_dentry_uuid}/uploadInfos/query"
    body = {
        "protocol": "HEADER_SIGNATURE",
        "unionId": union_id,
        "option": {"preCheckParam": {"name": file_name}},
    }
    return await dingtalk_post(path, token, body)


async def commit_file(parent_dentry_uuid: str, union_id: str, token: str, upload_key: str, file_name: str) -> dict:
    """步骤3: 提交文件，完成上传

    新版存储接口：POST /v2.0/storage/spaces/files/{parentDentryUuid}/commit
    返回 dentry，包含 id(文件dentryId)、spaceId、parentId(所在目录dentryId)、uuid 等。
    """
    path = f"/v2.0/storage/spaces/files/{parent_dentry_uuid}/commit"
    body = {
        "uploadKey": upload_key,
        "name": file_name,
        "unionId": union_id,
        "option": {"conflictStrategy": "AUTO_RENAME"},
    }
    return await dingtalk_post(path, token, body)


async def upload_to_root(
    file_bytes: bytes, file_name: str, root_dentry_uuid: str, union_id: str, token: str
) -> dict:
    """上传文件到知识库根目录（三步上传），返回文件 dentry 信息。

    注：知识库场景下文件名会被系统改写为数字，需在上层用 rename_file 改回正确名字。
    根目录用 rootDentryUuid(=rootNodeId) 作为 parentDentryUuid。
    """
    logger.info(f"开始上传文件: {file_name} ({len(file_bytes)} bytes)")

    # 步骤1: 获取上传信息
    upload_info = await get_upload_info(root_dentry_uuid, union_id, token, file_name)
    upload_key = upload_info["uploadKey"]
    header_sig = upload_info["headerSignatureInfo"]
    resource_url = header_sig["resourceUrls"][0]
    oss_headers = header_sig["headers"]
    logger.debug(f"获取上传信息成功, uploadKey={upload_key}")

    # 步骤2: 上传到 OSS（Content-Type 必须为空，否则签名校验失败）
    oss_headers = dict(oss_headers)
    oss_headers["Content-Type"] = ""
    await upload_to_oss(resource_url, oss_headers, file_bytes)
    logger.debug("OSS 上传完成")

    # 步骤3: 提交文件
    result = await commit_file(root_dentry_uuid, union_id, token, upload_key, file_name)
    dentry = result.get("dentry", {})
    logger.info(f"文件已提交: id={dentry.get('id')}, spaceId={dentry.get('spaceId')}")
    return dentry


async def move_file(
    space_id: str,
    dentry_id: str,
    target_space_id: str,
    target_folder_id: str,
    union_id: str,
    token: str,
) -> dict:
    """移动文件到指定文件夹。

    POST /v1.0/storage/spaces/{spaceId}/dentries/{dentryId}/move
    """
    path = f"/v1.0/storage/spaces/{space_id}/dentries/{dentry_id}/move"
    body = {
        "targetSpaceId": target_space_id,
        "targetFolderId": target_folder_id,
        "conflictStrategy": "AUTO_RENAME",
    }
    return await dingtalk_post(path, token, body, params={"unionId": union_id})


async def rename_file(space_id: str, dentry_id: str, new_name: str, union_id: str, token: str) -> dict:
    """重命名文件。

    POST /v1.0/storage/spaces/{spaceId}/dentries/{dentryId}/rename
    """
    path = f"/v1.0/storage/spaces/{space_id}/dentries/{dentry_id}/rename"
    return await dingtalk_post(path, token, {"newName": new_name}, params={"unionId": union_id})


async def rename_file_unique(
    space_id: str, dentry_id: str, file_name: str, union_id: str, token: str, max_retry: int = 20
) -> str:
    """重命名为目标文件名，遇重名自动追加 (1)(2)... 后缀。返回最终文件名。"""
    stem, ext = os.path.splitext(file_name)
    name = file_name
    for i in range(max_retry):
        try:
            result = await rename_file(space_id, dentry_id, name, union_id, token)
            final = result.get("dentry", {}).get("name", name)
            logger.info(f"重命名成功: {final}")
            return final
        except Exception as e:
            # 名字冲突时追加后缀重试
            if "already exist" in str(e).lower() or "AlreadyExist" in str(e):
                name = f"{stem}({i + 1}){ext}"
                continue
            raise
    logger.warning(f"重命名重试达上限，使用: {name}")
    return name
