"""
交易相关的 Pydantic 数据模型。
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SplitBase(BaseModel):
    """
    分录通用字段。
    """

    account_guid: str = Field(..., description="关联的科目 ID")
    amount: Decimal = Field(..., description="金额（借为正、贷为负）")
    memo: Optional[str] = Field(None, description="分录备注")
    cashflow_type_id: Optional[int] = Field(None, description="现金流量分类 ID")


class SplitCreate(SplitBase):
    """
    创建分录时使用的字段。
    """

    pass


class SplitResponse(SplitBase):
    """
    返回给前端的分录数据。
    """

    model_config = ConfigDict(from_attributes=True)

    guid: str = Field(..., description="分录唯一 ID")
    action: Optional[str] = Field(None, description="动作类型")
    reconcile_state: str = Field(..., description="对账状态")
    reconcile_date: Optional[date] = Field(None, description="对账日期")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class TransactionBase(BaseModel):
    """
    交易基础字段。
    """

    post_date: date = Field(..., description="记账日期")
    description: Optional[str] = Field(None, description="交易摘要")
    business_type: Optional[str] = Field(None, description="业务类型")
    reference_no: Optional[str] = Field(None, description="关联业务编号")


class TransactionCreate(TransactionBase):
    """
    创建交易时需要提交的数据。
    """

    num: Optional[str] = Field(None, description="凭证号")
    splits: List[SplitCreate] = Field(..., description="分录列表（至少两条）")

    @model_validator(mode="after")
    def ensure_double_entry(self) -> "TransactionCreate":
        """
        校验分录金额是否平衡。
        """
        if len(self.splits) < 2:
            raise ValueError("复式记账至少需要两条分录")
        total = sum(split.amount for split in self.splits)
        if total != Decimal("0"):
            raise ValueError("借贷必须平衡（所有金额之和需为 0）")
        return self


class TransactionResponse(TransactionBase):
    """
    返回给前端的交易数据。
    """

    model_config = ConfigDict(from_attributes=True)

    guid: str = Field(..., description="交易唯一 ID")
    num: Optional[str] = Field(None, description="凭证号")
    enter_date: datetime = Field(..., description="录入时间")
    splits: List[SplitResponse] = Field(..., description="分录明细")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

