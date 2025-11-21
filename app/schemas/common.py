"""
通用响应与报表相关的数据模型。
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """
    简单的消息返回结构。
    """

    message: str = Field(..., description="提示信息")


class AccountBalanceResponse(BaseModel):
    """
    对应数据库视图 `v_account_balance`。
    """

    account_guid: str = Field(..., description="科目 ID")
    account_name: str = Field(..., description="科目名称")
    account_type: str = Field(..., description="科目类别")
    balance: Decimal = Field(..., description="科目余额")


class TransactionDetailResponse(BaseModel):
    """
    对应数据库视图 `v_transaction_detail`。
    """

    tx_guid: str = Field(..., description="交易 ID")
    post_date: date = Field(..., description="记账日期")
    account_guid: str = Field(..., description="科目 ID")
    account_name: str = Field(..., description="科目名称")
    amount: Decimal = Field(..., description="金额（借贷相抵）")
    memo: Optional[str] = Field(None, description="分录备注")
    description: Optional[str] = Field(None, description="交易摘要")

