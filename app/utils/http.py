import httpx
from loguru import logger

# 钉钉 API 基础 URL
DINGTALK_BASE = "https://api.dingtalk.com"
DINGTALK_OAPI_BASE = "https://oapi.dingtalk.com"

# 复用同一个 httpx 客户端
_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=60)
    return _client


async def close_http_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def dingtalk_post(path: str, token: str, body: dict, params: dict = None) -> dict:
    """调用钉钉新版 API (api.dingtalk.com)"""
    client = await get_http_client()
    url = f"{DINGTALK_BASE}{path}"
    headers = {"x-acs-dingtalk-access-token": token}
    resp = await client.post(url, json=body, headers=headers, params=params)
    data = resp.json()
    logger.debug(f"POST {path} -> {resp.status_code}")
    if resp.status_code != 200 or "code" in data and data.get("code") != "success":
        error_msg = data.get("message", str(data))
        logger.error(f"钉钉API错误: POST {path} | {error_msg}")
        raise Exception(f"钉钉API错误: {error_msg}")
    return data


async def dingtalk_get(path: str, token: str, params: dict = None) -> dict:
    """调用钉钉新版 API GET"""
    client = await get_http_client()
    url = f"{DINGTALK_BASE}{path}"
    headers = {"x-acs-dingtalk-access-token": token}
    resp = await client.get(url, headers=headers, params=params)
    data = resp.json()
    logger.debug(f"GET {path} -> {resp.status_code}")
    if resp.status_code != 200 or "code" in data and data.get("code") != "success":
        error_msg = data.get("message", str(data))
        logger.error(f"钉钉API错误: GET {path} | {error_msg}")
        raise Exception(f"钉钉API错误: {error_msg}")
    return data


async def get_access_token_oapi(app_key: str, app_secret: str) -> dict:
    """调用旧版 OAPI 获取 access_token"""
    client = await get_http_client()
    url = f"{DINGTALK_OAPI_BASE}/gettoken"
    resp = await client.get(url, params={"appkey": app_key, "appsecret": app_secret})
    data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取Token失败: {data.get('errmsg', str(data))}")
    return data


async def upload_to_oss(resource_url: str, oss_headers: dict, file_bytes: bytes):
    """PUT 文件到阿里云 OSS"""
    client = await get_http_client()
    resp = await client.put(resource_url, content=file_bytes, headers=oss_headers)
    logger.debug(f"OSS PUT -> {resp.status_code}")
    if resp.status_code not in (200, 201, 204):
        raise Exception(f"OSS上传失败: HTTP {resp.status_code} {resp.text[:200]}")


async def download_file(url: str) -> bytes:
    """从 URL 下载文件内容"""
    client = await get_http_client()
    resp = await client.get(url, follow_redirects=True)
    if resp.status_code != 200:
        raise Exception(f"文件下载失败: HTTP {resp.status_code}")
    return resp.content
