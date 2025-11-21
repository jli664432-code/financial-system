"""
月度报表缓存模型。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class MonthlyReport(Base):
    """
    缓存每个月的报表快照，仅保留最近一次生成的月份。
    """

    __tablename__ = "monthly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_month: Mapped[date] = mapped_column(Date, nullable=False, doc="报表所属月份（取当月第一天）")
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, doc="报表类型：BALANCE/INCOME/CASHFLOW")
    payload: Mapped[str] = mapped_column(Text, nullable=False, doc="报表 JSON 数据")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        doc="生成时间",
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<MonthlyReport {self.report_month} {self.report_type}>"




