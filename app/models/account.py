"""
accounts 表的 ORM 模型定义。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .split import Split


class Account(Base):
    """
    会计科目模型，映射至数据库中的 `accounts` 表。
    """

    __tablename__ = "accounts"

    guid: Mapped[str] = mapped_column(String(32), primary_key=True, doc="科目唯一 ID")
    name: Mapped[str] = mapped_column(String(200), nullable=False, doc="科目名称")
    account_type: Mapped[str] = mapped_column(String(50), nullable=False, doc="科目类型")
    parent_guid: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("accounts.guid"),
        doc="父级科目 ID",
    )
    code: Mapped[Optional[str]] = mapped_column(String(50), doc="科目编码")
    description: Mapped[Optional[str]] = mapped_column(Text, doc="说明")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, doc="是否隐藏")
    placeholder: Mapped[bool] = mapped_column(Boolean, default=False, doc="是否仅作分类")
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        default=Decimal("0"),
        nullable=False,
        doc="当前余额，借为正贷为负",
    )
    is_cash: Mapped[bool] = mapped_column(Boolean, default=False, doc="是否现金/银行类科目")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="创建时间")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, doc="更新时间")

    parent: Mapped[Optional["Account"]] = relationship(
        "Account",
        remote_side="Account.guid",
        back_populates="children",
        doc="父级科目",
    )
    children: Mapped[List["Account"]] = relationship(
        "Account",
        back_populates="parent",
        doc="子科目列表",
    )

    splits: Mapped[List["Split"]] = relationship(
        "Split",
        back_populates="account",
        doc="关联的分录",
    )

