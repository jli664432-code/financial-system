"""
业务单据及业务流程相关的 Pydantic 模型。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BusinessDocumentType(str, Enum):
    """
    业务单据类型。
    """

    SALE = "SALE"
    PURCHASE = "PURCHASE"
    EXPENSE = "EXPENSE"
    CASHFLOW = "CASHFLOW"


class BusinessDocumentItemBase(BaseModel):
    """
    单据明细的通用字段，描述一对借贷科目与金额。
    """

    line_no: Optional[int] = Field(None, description="行号")
    description: Optional[str] = Field(None, description="明细描述")
    memo: Optional[str] = Field(None, description="备注")
    debit_account_guid: str = Field(..., description="借方科目 ID")
    credit_account_guid: str = Field(..., description="贷方科目 ID")
    amount: Decimal = Field(..., gt=Decimal("0"), description="金额（正数）")
    quantity: Optional[Decimal] = Field(None, description="数量")
    unit_price: Optional[Decimal] = Field(None, description="单价")
    cashflow_type_id: Optional[int] = Field(None, description="行级现金流量分类")

    @model_validator(mode="after")
    def ensure_amount_positive(self) -> "BusinessDocumentItemBase":
        if self.amount <= Decimal("0"):
            raise ValueError("明细金额必须为正数")
        return self


class BusinessDocumentItemCreate(BusinessDocumentItemBase):
    """
    创建业务单据时的明细结构。
    """

    pass


class BusinessDocumentItemResponse(BusinessDocumentItemBase):
    """
    返回给前端的明细结构。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="明细 ID")
    document_id: int = Field(..., description="所属单据 ID")
    created_at: datetime = Field(..., description="创建时间")


class BusinessDocumentBase(BaseModel):
    """
    业务单据公共字段。
    """

    doc_no: Optional[str] = Field(None, description="单据编号")
    doc_date: date = Field(..., description="业务日期")
    partner_name: Optional[str] = Field(None, description="往来单位/员工")
    reference_no: Optional[str] = Field(None, description="外部参考号")
    description: Optional[str] = Field(None, description="摘要说明")
    currency: str = Field("CNY", description="币种")
    cashflow_type_id: Optional[int] = Field(None, description="默认现金流分类")
    items: List[BusinessDocumentItemCreate] = Field(..., description="单据明细")

    @model_validator(mode="after")
    def ensure_items(self) -> "BusinessDocumentBase":
        if not self.items:
            raise ValueError("单据至少需要一条明细")
        return self


class BusinessDocumentCreate(BusinessDocumentBase):
    """
    通用的业务单据创建结构。
    """

    pass


class SalesDocumentCreate(BusinessDocumentCreate):
    """
    销售业务单据。
    """

    pass


class PurchaseDocumentCreate(BusinessDocumentCreate):
    """
    采购业务单据。
    """

    pass


class ExpenseDocumentCreate(BusinessDocumentCreate):
    """
    费用报销单。
    """

    pass


class CashflowDocumentCreate(BusinessDocumentCreate):
    """
    收付款单（现金流量业务）。
    """

    pass


class BusinessDocumentResponse(BusinessDocumentBase):
    """
    返回给前端的业务单据结构。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="单据 ID")
    doc_type: BusinessDocumentType = Field(..., description="单据类型")
    status: str = Field(..., description="单据状态")
    total_amount: Decimal = Field(..., description="合计金额")
    transaction_guid: str = Field(..., description="关联凭证 ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    items: List[BusinessDocumentItemResponse] = Field(..., description="明细列表")


