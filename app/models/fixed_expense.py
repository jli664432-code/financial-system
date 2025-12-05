"""
固定费用配置模型。
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .account import Account


class FixedExpense(Base):
    """
    每月自动扣除的固定费用配置。
    """

    __tablename__ = "fixed_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, doc="费用名称")
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, doc="固定扣款金额（借方金额，单位：元）"
    )
    expense_account_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        nullable=False,
        doc="费用将记入的科目（借方）",
    )
    primary_account_guid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        nullable=False,
        doc="优先扣款的科目（通常为库存现金）",
    )
    fallback_account_guid: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        doc="备用扣款科目（通常为银行存款）",
    )
    day_of_month: Mapped[int] = mapped_column(
        Integer, default=1, doc="预计扣款日（1-28）"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, doc="是否启用")
    last_run_month: Mapped[Optional[date]] = mapped_column(
        Date, doc="上一次成功扣款的月份（取当月1日）"
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, doc="上一次扣款时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    expense_account: Mapped[Account] = relationship(
        "Account", foreign_keys=[expense_account_guid]
    )
    primary_account: Mapped[Account] = relationship(
        "Account",
        foreign_keys=[primary_account_guid],
        overlaps="expense_account,fallback_account",
    )
    fallback_account: Mapped[Optional[Account]] = relationship(
        "Account",
        foreign_keys=[fallback_account_guid],
        overlaps="expense_account,primary_account",
    )


