"""
cashflow_types 表的 ORM 模型定义。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .split import Split


class CashflowType(Base):
    """
    现金流量分类，用于标记分录属于经营/投资/筹资的哪一类。
    """

    __tablename__ = "cashflow_types"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="主键",
    )
    code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
        doc="分类编码",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="分类名称",
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        doc="对应的现金流量三大分类",
    )
    flow_type: Mapped[str] = mapped_column(
        Enum("OPERATING", "INVESTING", "FINANCING", name="flow_type_enum"),
        nullable=False,
        doc="现金流量类型：经营/投资/筹资",
    )
    direction: Mapped[str] = mapped_column(
        Enum("INFLOW", "OUTFLOW", name="direction_enum"),
        nullable=False,
        doc="现金流方向（INFLOW/OUTFLOW）",
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        default=True,
        doc="是否启用",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        doc="排序值",
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        doc="创建时间",
    )

    splits: Mapped[List["Split"]] = relationship(
        "Split",
        back_populates="cashflow_type",
        doc="引用该分类的分录",
    )


