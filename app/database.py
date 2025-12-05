"""
数据库连接与 Session 管理模块。
"""
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """
    SQLAlchemy Declarative 基类，所有模型都将继承它。
    """


def _get_ssl_config() -> Dict[str, Any]:
    """
    从环境变量读取 SSL 配置（用于云端 MySQL 连接）。
    
    支持的环境变量：
    - DB_SSL_CA: CA 证书文件路径
    - DB_SSL_CERT: 客户端证书文件路径
    - DB_SSL_KEY: 客户端密钥文件路径
    - DB_SSL_DISABLE_VERIFY: 是否禁用证书验证（仅用于测试，生产环境不推荐）
    """
    ssl_config: Dict[str, Any] = {}
    
    # 如果设置了禁用验证（仅用于测试）
    if os.getenv("DB_SSL_DISABLE_VERIFY", "").lower() in ("true", "1", "yes"):
        ssl_config = {
            "check_hostname": False,
            "verify_mode": 0,
        }
        return ssl_config
    
    # 检查是否有 SSL 证书文件配置
    ca_path = os.getenv("DB_SSL_CA")
    cert_path = os.getenv("DB_SSL_CERT")
    key_path = os.getenv("DB_SSL_KEY")
    
    if ca_path or cert_path or key_path:
        ssl_config = {}
        if ca_path:
            ca_full_path = Path(__file__).parent.parent / ca_path
            if ca_full_path.exists():
                ssl_config["ca"] = str(ca_full_path)
        if cert_path:
            cert_full_path = Path(__file__).parent.parent / cert_path
            if cert_full_path.exists():
                ssl_config["cert"] = str(cert_full_path)
        if key_path:
            key_full_path = Path(__file__).parent.parent / key_path
            if key_full_path.exists():
                ssl_config["key"] = str(key_full_path)
        
        if ssl_config:
            return ssl_config
    
    return {}


# 构建连接参数
connect_args: Dict[str, Any] = {}
ssl_config = _get_ssl_config()
if ssl_config:
    connect_args["ssl"] = ssl_config

# 连接超时设置（云端数据库建议设置）
connect_timeout = os.getenv("DB_CONNECT_TIMEOUT", "10")
try:
    connect_args["connect_timeout"] = int(connect_timeout)
except ValueError:
    pass

# 创建 SQLAlchemy Engine（连接池）
engine = create_engine(
    get_settings().database_url,
    echo=False,  # 生产环境建议设为 False，调试时可改为 True
    pool_pre_ping=True,  # 避免长时间闲置后连接失效
    pool_size=10,  # 连接池大小（可根据实际情况调整）
    max_overflow=20,  # 最大溢出连接数
    pool_recycle=3600,  # 连接回收时间（秒）
    connect_args=connect_args if connect_args else None,
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

