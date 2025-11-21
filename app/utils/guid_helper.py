"""
GUID 生成工具函数。
"""
from uuid import uuid4


def generate_guid() -> str:
    """
    生成 32 位十六进制字符串，适用于数据库中的 `guid` 字段。
    """
    return uuid4().hex

