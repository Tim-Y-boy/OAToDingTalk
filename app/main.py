import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.routers import upload
from app.services.token import token_manager
from app.utils.http import close_http_client

# loguru 配置
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
logger.add("logs/app_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", level="DEBUG")

scheduler = AsyncIOScheduler()


async def _refresh_token_job():
    try:
        await token_manager.refresh()
    except Exception as e:
        logger.error(f"定时刷新Token失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    settings = get_settings()
    logger.info("服务启动中...")
    await token_manager.refresh()

    # 每 110 分钟刷新一次 token
    scheduler.add_job(_refresh_token_job, "interval", minutes=110, id="refresh_token")
    scheduler.start()
    logger.info(f"服务已启动, 端口={settings.port}")

    yield

    # 关闭时
    scheduler.shutdown(wait=False)
    await close_http_client()
    logger.info("服务已停止")


app = FastAPI(
    title="钉钉知识库文件上传服务",
    description="接收OA系统推送的PDF文件，上传到钉钉知识库并按日期归档",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(upload.router)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
