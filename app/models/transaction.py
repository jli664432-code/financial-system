"""
transactions 表的 ORM 模型定义。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .split import Split


class Transaction(Base):
    """
    交易（凭证）模型。
    """

    __tablename__ = "transactions"

    guid: Mapped[str] = mapped_column(String(32), primary_key=True, doc="交易唯一 ID")
    num: Mapped[Optional[str]] = mapped_column(String(50), doc="凭证号")
    post_date: Mapped[date] = mapped_column(Date, nullable=False, doc="记账日期")
    enter_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, doc="录入时间")
    description: Mapped[Optional[str]] = mapped_column(String(500), doc="摘要")
    business_type: Mapped[Optional[str]] = mapped_column(String(50), doc="业务类型")
    reference_no: Mapped[Optional[str]] = mapped_column(String(100), doc="业务参考号")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="创建时间")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="更新时间")

    splits: Mapped[List["Split"]] = relationship(
        "Split",
        back_populates="transaction",
        cascade="all, delete-orphan",
        doc="关联的分录明细",
    )

