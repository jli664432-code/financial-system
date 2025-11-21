"""
业务单据主表与明细表模型。
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .account import Account
    from .cashflow_type import CashflowType
    from .transaction import Transaction


class BusinessDocument(Base):
    """
    业务单据主表，一张业务单据会自动关联一张会计凭证。
    """

    __tablename__ = "business_documents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="主键",
    )
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False, doc="单据类型")
    doc_no: Mapped[Optional[str]] = mapped_column(String(50), doc="单据编号")
    doc_date: Mapped[date] = mapped_column(Date, nullable=False, doc="业务日期")
    partner_name: Mapped[Optional[str]] = mapped_column(String(200), doc="往来单位/员工")
    reference_no: Mapped[Optional[str]] = mapped_column(String(100), doc="外部参考号")
    description: Mapped[Optional[str]] = mapped_column(String(500), doc="摘要说明")
    currency: Mapped[str] = mapped_column(String(10), default="CNY", doc="币种")
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        doc="本单据金额合计（正值）",
    )
    status: Mapped[str] = mapped_column(String(20), default="POSTED", doc="当前状态")
    transaction_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("transactions.guid"),
        doc="自动生成的会计凭证 ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        doc="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        doc="最后更新时间",
    )

    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        doc="对应的会计凭证",
    )
    items: Mapped[List["BusinessDocumentItem"]] = relationship(
        "BusinessDocumentItem",
        back_populates="document",
        cascade="all, delete-orphan",
        doc="单据明细",
    )


class BusinessDocumentItem(Base):
    """
    业务单据明细表。
    """

    __tablename__ = "business_document_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="明细主键",
    )
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("business_documents.id"),
        nullable=False,
        doc="所属单据 ID",
    )
    line_no: Mapped[int] = mapped_column(Integer, doc="行号")
    description: Mapped[Optional[str]] = mapped_column(String(500), doc="行描述")
    memo: Mapped[Optional[str]] = mapped_column(String(500), doc="备注")
    debit_account_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        nullable=False,
        doc="借方科目",
    )
    credit_account_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        nullable=False,
        doc="贷方科目",
    )
    quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        doc="数量",
    )
    unit_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        doc="单价",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        doc="金额（正值）",
    )
    cashflow_type_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("cashflow_types.id"),
        doc="现金流量分类",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        doc="创建时间",
    )

    document: Mapped["BusinessDocument"] = relationship(
        "BusinessDocument",
        back_populates="items",
        doc="所属单据",
    )
    debit_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[debit_account_guid],
        doc="借方科目",
    )
    credit_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[credit_account_guid],
        doc="贷方科目",
    )
    cashflow_type: Mapped[Optional["CashflowType"]] = relationship(
        "CashflowType",
        doc="明细对应的现金流量分类",
    )


