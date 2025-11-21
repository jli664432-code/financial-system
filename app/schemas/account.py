"""
账户相关的 Pydantic 数据模型。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class AccountBase(BaseModel):
    """
    通用的账户信息字段。
    """

    guid: str = Field(..., description="科目唯一 ID")
    name: str = Field(..., description="科目名称")
    account_type: str = Field(..., description="科目类型")
    parent_guid: Optional[str] = Field(None, description="父级科目 ID")
    code: Optional[str] = Field(None, description="科目编码")
    description: Optional[str] = Field(None, description="科目说明")
    hidden: bool = Field(False, description="是否隐藏")
    placeholder: bool = Field(False, description="是否仅作分类")
    current_balance: Decimal = Field(Decimal("0"), description="当前余额")
    is_cash: bool = Field(False, description="是否现金/银行类科目")


class AccountCreate(BaseModel):
    """
    创建科目时的数据结构。
    """
    
    name: str = Field(..., description="科目名称")
    account_type: str = Field(..., description="科目类型")
    code: Optional[str] = Field(None, description="科目编码")
    parent_guid: Optional[str] = Field(None, description="父级科目 ID")
    description: Optional[str] = Field(None, description="科目说明")
    hidden: bool = Field(False, description="是否隐藏")
    placeholder: bool = Field(False, description="是否仅作分类")
    is_cash: bool = Field(False, description="是否现金/银行类科目")


class AccountUpdate(BaseModel):
    """
    更新科目时的数据结构。
    """
    
    name: Optional[str] = Field(None, description="科目名称")
    account_type: Optional[str] = Field(None, description="科目类型")
    code: Optional[str] = Field(None, description="科目编码")
    parent_guid: Optional[str] = Field(None, description="父级科目 ID")
    description: Optional[str] = Field(None, description="科目说明")
    hidden: Optional[bool] = Field(None, description="是否隐藏")
    placeholder: Optional[bool] = Field(None, description="是否仅作分类")
    is_cash: Optional[bool] = Field(None, description="是否现金/银行类科目")


class AccountResponse(AccountBase):
    """
    返回给前端的账户信息。
    """

    model_config = ConfigDict(from_attributes=True)

    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

