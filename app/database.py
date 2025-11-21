"""
数据库连接与 Session 管理模块。
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """
    SQLAlchemy Declarative 基类，所有模型都将继承它。
    """


# 创建 SQLAlchemy Engine（连接池）
engine = create_engine(
    get_settings().database_url,
    echo=True,  # 如需调试 SQL，可改为 True
    pool_pre_ping=True,  # 避免长时间闲置后连接失效
)

# 创建 Session 工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    提供一个简单的上下文管理器，自动提交或回滚事务。

    使用示例：

    ```
    with session_scope() as session:
        session.add(obj)
    ```
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入用的数据库会话生成器。
    """
    with session_scope() as session:
        yield session

