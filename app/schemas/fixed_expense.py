"""
固定费用相关的 Pydantic 模型。
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, conint


class FixedExpenseBase(BaseModel):
    name: str = Field(..., description="费用名称")
    amount: Decimal = Field(..., gt=0, description="固定扣款金额")
    expense_account_guid: str = Field(..., description="费用所属科目（借方）")
    primary_account_guid: str = Field(..., description="优先扣款科目（库存现金）")
    fallback_account_guid: Optional[str] = Field(
        None, description="备用扣款科目（银行存款）"
    )
    day_of_month: conint(ge=1, le=28) = Field(
        1, description="预计扣款日（1-28）"
    )
    is_active: bool = Field(True, description="是否启用")


class FixedExpenseCreate(FixedExpenseBase):
    pass


class FixedExpenseUpdate(FixedExpenseBase):
    pass


class FixedExpenseResponse(FixedExpenseBase):
    id: int
    last_run_month: Optional[date] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



