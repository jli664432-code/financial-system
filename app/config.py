"""
应用配置模块。

本示例使用 `python-dotenv` 从根目录的 `.env` 文件加载数据库配置，
并提供一个简洁的 `Settings` 对象给其他模块使用。
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


# 先尝试在项目根目录寻找 .env 文件并加载环境变量
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)


class Settings(BaseModel):
    """
    保存项目配置的 Pydantic 模型。

    - `database_url`：SQLAlchemy 识别的数据库连接串。
    - `app_title`：FastAPI 项目标题。
    - `app_version`：FastAPI 项目版本。
    """

    database_url: str = Field(
        default="mysql+pymysql://root:password@127.0.0.1:3306/accounting_system",
        description="MySQL 数据库连接 URL，请根据实际情况修改。",
    )
    app_title: str = Field(default="财务记账系统", description="FastAPI 文档标题")
    app_version: str = Field(default="0.1.0", description="API 版本号")


@lru_cache
def get_settings() -> Settings:
    """
    返回单例的 Settings，避免重复加载环境变量。
    """
    database_url = os.getenv("DATABASE_URL")
    return Settings(database_url=database_url) if database_url else Settings()

