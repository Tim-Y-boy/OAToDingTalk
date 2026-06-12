from datetime import date
from fastapi import APIRouter, UploadFile, File, Request, Header, Form, HTTPException
from typing import Optional
from loguru import logger

from app.models import UploadByUrlRequest, UploadResponse, HealthResponse
from app.config import get_settings
from app.services.token import token_manager
from app.services.folder import folder_manager
from app.services.dingtalk import upload_to_root, move_file, rename_file_unique
from app.utils.http import download_file

router = APIRouter(prefix="/api")


def verify_api_key(request: Request):
    """简单 API Key 鉴权"""
    settings = get_settings()
    key = request.headers.get("X-API-Key", "")
    if key != settings.api_key:
        raise HTTPException(status_code=401, detail="无效的 API Key")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        token_valid=token_manager.is_valid,
        token_expire_at=token_manager.expire_at_str,
    )


@router.post("/upload/file", response_model=UploadResponse)
async def upload_by_file(
    request: Request,
    file: UploadFile = File(...),
    date: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
):
    """接口1: 通过文件流直传上传 PDF 到钉钉知识库"""
    verify_api_key(request)

    # 读取文件
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        return UploadResponse(success=False, message="文件内容为空")
    if len(file_bytes) > 100 * 1024 * 1024:
        return UploadResponse(success=False, message="文件超过100MB限制")

    # 确定文件名
    file_name = name or file.filename or "未命名.pdf"
    if not file_name.lower().endswith(".pdf"):
        file_name += ".pdf"

    # 确定日期
    date_str = date or date.today().isoformat()

    return await _do_upload(file_bytes, file_name, date_str)


@router.post("/upload/url", response_model=UploadResponse)
async def upload_by_url(request: Request, body: UploadByUrlRequest):
    """接口2: 通过文件下载URL上传到钉钉知识库"""
    verify_api_key(request)

    # 下载文件
    try:
        file_bytes = await download_file(body.file_url)
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return UploadResponse(success=False, message=f"文件下载失败: {e}")

    if len(file_bytes) == 0:
        return UploadResponse(success=False, message="下载的文件内容为空")

    # 确定文件名
    file_name = body.file_name
    if not file_name.lower().endswith(".pdf"):
        file_name += ".pdf"

    # 确定日期
    date_str = body.date or date.today().isoformat()

    return await _do_upload(file_bytes, file_name, date_str)


async def _do_upload(file_bytes: bytes, file_name: str, date_str: str) -> UploadResponse:
    """通用上传逻辑: 上传到根目录 → 建日期文件夹 → 移入文件夹 → 重命名

    知识库(alidocs)的存储接口限制: 文件只能上传到根目录(子目录直传报500)，
    且文件名会被系统改写为数字。因此采用「上传到根 → 建文件夹 → move → rename」
    四步完成按日期归档。
    """
    try:
        settings = get_settings()
        union_id = settings.dingtalk_admin_union_id
        root_uuid = settings.dingtalk_root_dentry_uuid
        token = await token_manager.get_token()

        # 1. 上传到知识库根目录，拿到文件 dentryId、spaceId、根目录 parentId
        dentry = await upload_to_root(file_bytes, file_name, root_uuid, union_id, token)
        space_id = dentry["spaceId"]
        root_parent_id = dentry["parentId"]
        file_id = dentry["id"]

        # 2. 确保日期文件夹存在
        folder_name, folder_id = await folder_manager.ensure_folder(
            space_id, root_parent_id, date_str, token
        )

        # 3. 移动文件到日期文件夹
        await move_file(space_id, file_id, space_id, folder_id, union_id, token)

        # 4. 重命名为正确文件名(同名自动加后缀)
        final_name = await rename_file_unique(space_id, file_id, file_name, union_id, token)

        dentry_uuid = dentry.get("uuid", "")
        return UploadResponse(
            success=True,
            dentry_uuid=dentry_uuid,
            folder=folder_name,
            file_name=final_name,
        )
    except Exception as e:
        logger.error(f"上传失败: {e}")
        return UploadResponse(success=False, message=str(e))
