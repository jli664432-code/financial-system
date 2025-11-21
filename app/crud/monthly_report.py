"""
月度报表缓存相关的数据库操作。
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import MonthlyReport


def _month_key(target_date: date) -> date:
    return target_date.replace(day=1)


def get_reports_for_month(db: Session, report_month: date) -> Dict[str, dict]:
    """
    查询指定月份的所有报表缓存。
    """
    stmt = select(MonthlyReport).where(MonthlyReport.report_month == _month_key(report_month))
    rows = db.scalars(stmt).all()
    result: Dict[str, dict] = {}
    for row in rows:
        try:
            payload = json.loads(row.payload)
        except json.JSONDecodeError:
            payload = {}
        result[row.report_type] = payload
    return result


def replace_reports(
    db: Session,
    report_month: date,
    reports: Dict[str, dict],
) -> None:
    """
    删除现有报表并写入新的月份报表。
    """
    db.execute(delete(MonthlyReport))
    month_key = _month_key(report_month)
    now = datetime.utcnow()

    for report_type, payload in reports.items():
        record = MonthlyReport(
            report_month=month_key,
            report_type=report_type,
            payload=json.dumps(payload, default=str),
            created_at=now,
        )
        db.add(record)


def get_current_cached_month(db: Session) -> Optional[date]:
    """
    返回当前缓存的报表月份（如果存在）。
    """
    stmt = select(MonthlyReport.report_month).limit(1)
    month = db.scalar(stmt)
    return month

