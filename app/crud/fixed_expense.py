"""
固定费用相关的数据库操作。
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Account, FixedExpense
from ..schemas.fixed_expense import FixedExpenseCreate, FixedExpenseUpdate
from ..schemas.transaction import TransactionCreate, SplitCreate
from . import transaction as transaction_crud


def list_fixed_expenses(db: Session) -> List[FixedExpense]:
    """
    查询全部固定费用配置。
    """
    stmt = select(FixedExpense).order_by(FixedExpense.day_of_month, FixedExpense.id)
    return list(db.scalars(stmt).all())


def get_fixed_expense(db: Session, expense_id: int) -> Optional[FixedExpense]:
    """
    根据主键获取固定费用配置。
    """
    return db.get(FixedExpense, expense_id)


def create_fixed_expense(db: Session, data: FixedExpenseCreate) -> FixedExpense:
    """
    新建固定费用配置。
    """
    _validate_accounts(db, data)
    expense = FixedExpense(
        name=data.name,
        amount=data.amount,
        expense_account_guid=data.expense_account_guid,
        primary_account_guid=data.primary_account_guid,
        fallback_account_guid=data.fallback_account_guid,
        day_of_month=data.day_of_month,
        is_active=data.is_active,
    )
    db.add(expense)
    return expense


def update_fixed_expense(
    db: Session,
    expense_id: int,
    data: FixedExpenseUpdate,
) -> FixedExpense:
    """
    更新固定费用配置。
    """
    expense = get_fixed_expense(db, expense_id)
    if expense is None:
        raise ValueError(f"固定费用 {expense_id} 不存在")

    _validate_accounts(db, data)

    expense.name = data.name
    expense.amount = data.amount
    expense.expense_account_guid = data.expense_account_guid
    expense.primary_account_guid = data.primary_account_guid
    expense.fallback_account_guid = data.fallback_account_guid
    expense.day_of_month = data.day_of_month
    expense.is_active = data.is_active
    expense.updated_at = datetime.utcnow()
    return expense


def delete_fixed_expense(db: Session, expense_id: int) -> None:
    """
    删除固定费用配置。
    """
    expense = get_fixed_expense(db, expense_id)
    if expense is None:
        raise ValueError(f"固定费用 {expense_id} 不存在")
    db.delete(expense)


def execute_fixed_expense(
    db: Session,
    expense: FixedExpense,
    run_date: Optional[date] = None,
    *,
    force: bool = False,
) -> Tuple[Optional[str], List[str]]:
    """
    执行单个固定费用扣款。

    Returns:
        (transaction_guid, warnings)
    """
    run_date = run_date or date.today()
    if not expense.is_active:
        return None, ["该固定费用已停用，未执行。"]

    if not force and not is_due(expense, run_date):
        due_day = min(expense.day_of_month, monthrange(run_date.year, run_date.month)[1])
        return None, [f"尚未到扣款日期（{due_day} 日），未执行。"]

    amount = Decimal(expense.amount)
    if amount <= 0:
        return None, ["金额必须大于 0，未执行。"]

    # 选择扣款科目
    pay_account_guid, warnings = _select_payment_account(db, expense, amount)
    if pay_account_guid is None:
        warnings.append("未配置可用的支付科目，未执行。")
        return None, warnings

    description = f"{run_date:%Y年%m月} {expense.name} 固定费用"
    tx_data = TransactionCreate(
        post_date=run_date,
        description=description,
        num=None,
        splits=[
            SplitCreate(
                account_guid=expense.expense_account_guid,
                amount=amount,
                memo=f"{expense.name} 自动扣费",
            ),
            SplitCreate(
                account_guid=pay_account_guid,
                amount=-amount,
                memo=f"{expense.name} 自动扣费",
            ),
        ],
    )
    transaction = transaction_crud.create_transaction(db, tx_data)

    month_start = run_date.replace(day=1)
    expense.last_run_month = month_start
    expense.last_run_at = datetime.utcnow()

    return transaction.guid, warnings


def execute_all_due_fixed_expenses(
    db: Session,
    run_date: Optional[date] = None,
) -> List[Tuple[FixedExpense, Optional[str], List[str]]]:
    """
    执行所有到期的固定费用。

    Returns:
        列表，包含 (expense, transaction_guid, warnings)
    """
    run_date = run_date or date.today()
    results = []
    expenses = list_fixed_expenses(db)
    for expense in expenses:
        if not expense.is_active:
            continue
        if not is_due(expense, run_date):
            continue
        tx_guid, warnings = execute_fixed_expense(db, expense, run_date=run_date, force=True)
        results.append((expense, tx_guid, warnings))
    return results


def is_due(expense: FixedExpense, target_date: date) -> bool:
    """
    判断在指定日期是否需要执行扣款。
    """
    month_start = target_date.replace(day=1)
    if expense.last_run_month == month_start:
        return False

    max_day = monthrange(target_date.year, target_date.month)[1]
    due_day = min(max(expense.day_of_month, 1), max_day)
    due_date = month_start.replace(day=due_day)
    return target_date >= due_date


def _validate_accounts(db: Session, data: FixedExpenseCreate | FixedExpenseUpdate) -> None:
    """
    校验配置中引用的科目是否存在。
    """
    for guid_field in [
        ("expense_account_guid", data.expense_account_guid),
        ("primary_account_guid", data.primary_account_guid),
        ("fallback_account_guid", data.fallback_account_guid),
    ]:
        field_name, guid = guid_field
        if guid:
            account = db.get(Account, guid)
            if account is None:
                raise ValueError(f"{field_name} 指向的科目不存在")


def _select_payment_account(
    db: Session,
    expense: FixedExpense,
    amount: Decimal,
) -> Tuple[Optional[str], List[str]]:
    """
    根据余额选择付款科目，返回 (account_guid, warnings)。
    """
    warnings: List[str] = []
    primary = db.get(Account, expense.primary_account_guid) if expense.primary_account_guid else None
    fallback = db.get(Account, expense.fallback_account_guid) if expense.fallback_account_guid else None

    primary_balance = primary.current_balance if primary else None
    fallback_balance = fallback.current_balance if fallback else None

    if primary and (primary_balance or Decimal("0")) >= amount:
        return primary.guid, warnings

    if primary:
        warnings.append(
            f"主支付科目 {primary.name} 余额不足（当前 {primary_balance or 0}），改用备用科目。"
        )
    else:
        warnings.append("未配置主支付科目。")

    if fallback:
        if (fallback_balance or Decimal("0")) < amount:
            warnings.append(
                f"备用科目 {fallback.name} 余额也不足（当前 {fallback_balance or 0}），扣费后余额可能为负数。"
            )
        return fallback.guid, warnings

    warnings.append("未配置备用科目，仍使用主科目扣费。")
    return expense.primary_account_guid, warnings



