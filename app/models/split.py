"""
splits 表的 ORM 模型定义。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, CHAR, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .account import Account
    from .cashflow_type import CashflowType
    from .transaction import Transaction


class Split(Base):
    """
    分录明细模型。
    """

    __tablename__ = "splits"

    guid: Mapped[str] = mapped_column(String(32), primary_key=True, doc="分录唯一 ID")
    tx_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("transactions.guid"),
        nullable=False,
        doc="关联的交易 ID",
    )
    account_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        nullable=False,
        doc="关联的科目 ID",
    )
    memo: Mapped[Optional[str]] = mapped_column(String(500), doc="分录备注")
    action: Mapped[Optional[str]] = mapped_column(String(50), doc="动作类型")
    reconcile_state: Mapped[str] = mapped_column(CHAR(1), default="n", doc="对账状态")
    reconcile_date: Mapped[Optional[date]] = mapped_column(Date, doc="对账日期")
    value_num: Mapped[int] = mapped_column(BigInteger, nullable=False, doc="金额分子")
    value_denom: Mapped[int] = mapped_column(BigInteger, default=1, doc="金额分母")
    cashflow_type_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("cashflow_types.id"),
        doc="现金流量分类",
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="创建时间")

    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="splits",
        doc="所属交易",
    )
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="splits",
        doc="所属科目",
    )
    cashflow_type: Mapped[Optional["CashflowType"]] = relationship(
        "CashflowType",
        back_populates="splits",
        doc="关联的现金流量分类",
    )

    @property
    def amount(self) -> Decimal:
        """
        快捷属性：把分数形式的金额转回 Decimal。
        """
        denominator = self.value_denom or 1
        return Decimal(self.value_num) / Decimal(denominator)

