"""
FastAPI 入口文件。

运行项目：

```
uvicorn app.main:app --reload
```
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import accounts, transactions, pages, business
from .config import get_settings


def create_app() -> FastAPI:
    """
    工厂函数：创建并配置 FastAPI 实例。
    """
    settings = get_settings()
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 注册路由
    app.include_router(pages.router)
    app.include_router(accounts.router)
    app.include_router(transactions.router)
    app.include_router(business.router)

    @app.get("/", tags=["系统"])
    def root():
        """
        简单返回欢迎信息，便于测试服务是否启动成功。
        """
        return {"message": "欢迎使用财务记账系统 API"}

    return app


app = create_app()

