"""
交易相关的数据库操作。
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Account, Transaction, Split, v_transaction_detail
from ..schemas.transaction import TransactionCreate
from ..utils.amount_helper import decimal_to_fraction
from ..utils.guid_helper import generate_guid


def list_transactions(db: Session, limit: int = 50) -> List[Transaction]:
    """
    查询最近的交易记录。
    """
    stmt = (
        select(Transaction)
        .order_by(Transaction.post_date.desc(), Transaction.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique().all())


def get_transaction(db: Session, guid: str) -> Optional[Transaction]:
    """
    根据主键查询单笔交易。
    """
    return db.get(Transaction, guid)


def list_transaction_details(
    db: Session,
    tx_guid: Optional[str] = None,
    limit: int = 100,
):
    """
    查询交易明细视图，可选按交易 ID 过滤。
    """
    stmt = select(v_transaction_detail)
    if tx_guid:
        # 尝试使用 tx_guid 字段过滤
        try:
            stmt = stmt.where(v_transaction_detail.c.tx_guid == tx_guid)
        except (AttributeError, KeyError):
            try:
                stmt = stmt.where(v_transaction_detail.c.transaction_guid == tx_guid)
            except (AttributeError, KeyError):
                # 如果字段不存在，跳过过滤
                pass
        except Exception:  # noqa: BLE001
            pass
    
    # 尝试按 post_date 排序，如果字段不存在则跳过排序
    try:
        stmt = stmt.order_by(v_transaction_detail.c.post_date.desc())
    except (AttributeError, KeyError):
        try:
            stmt = stmt.order_by(v_transaction_detail.c.date.desc())
        except (AttributeError, KeyError):
            try:
                stmt = stmt.order_by(v_transaction_detail.c.tx_guid.desc())
            except (AttributeError, KeyError):
                # 如果所有字段都不存在，不排序
                pass
    except Exception:  # noqa: BLE001
        # 如果排序失败，直接返回不排序的结果
        pass
    
    stmt = stmt.limit(limit)
    return db.execute(stmt).mappings().all()


def create_transaction(db: Session, data: TransactionCreate) -> Transaction:
    """
    创建交易及其分录。
    """
    now = datetime.utcnow()
    tx_guid = generate_guid()
    transaction = Transaction(
        guid=tx_guid,
        num=data.num,
        post_date=data.post_date,
        enter_date=now,
        description=data.description,
        business_type=data.business_type,
        reference_no=data.reference_no,
        created_at=now,
        updated_at=now,
    )

    balance_changes: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    splits: List[Split] = []
    for split_data in data.splits:
        value_num, value_denom = decimal_to_fraction(split_data.amount)
        split = Split(
            guid=generate_guid(),
            tx_guid=tx_guid,
            account_guid=split_data.account_guid,
            memo=split_data.memo,
            action=None,
            reconcile_state="n",
            value_num=value_num,
            value_denom=value_denom,
            cashflow_type_id=split_data.cashflow_type_id,
            created_at=now,
        )
        splits.append(split)
        balance_changes[split_data.account_guid] += split_data.amount

    transaction.splits = splits
    db.add(transaction)
    _apply_balance_changes(db, balance_changes, now)
    return transaction


def update_transaction(db: Session, guid: str, data: TransactionCreate) -> Transaction:
    """
    更新已存在的交易及其分录。
    """
    transaction = db.get(Transaction, guid)
    if transaction is None:
        raise ValueError(f"交易 {guid} 不存在，无法更新")

    now = datetime.utcnow()

    # 回滚旧分录对余额的影响
    revert_changes: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for split in transaction.splits:
        amount = _split_amount(split)
        revert_changes[split.account_guid] -= amount
    _apply_balance_changes(db, revert_changes, now)

    # 清理旧分录
    for split in list(transaction.splits):
        db.delete(split)
    db.flush()

    # 更新交易基本信息
    transaction.num = data.num
    transaction.post_date = data.post_date
    transaction.description = data.description
    transaction.business_type = data.business_type
    transaction.reference_no = data.reference_no
    transaction.updated_at = now

    # 创建新的分录
    balance_changes: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    splits: List[Split] = []
    for split_data in data.splits:
        value_num, value_denom = decimal_to_fraction(split_data.amount)
        split = Split(
            guid=generate_guid(),
            tx_guid=transaction.guid,
            account_guid=split_data.account_guid,
            memo=split_data.memo,
            action=None,
            reconcile_state="n",
            value_num=value_num,
            value_denom=value_denom,
            cashflow_type_id=split_data.cashflow_type_id,
            created_at=now,
        )
        splits.append(split)
        balance_changes[split_data.account_guid] += split_data.amount

    transaction.splits = splits
    _apply_balance_changes(db, balance_changes, now)
    return transaction


def delete_transaction(db: Session, guid: str) -> None:
    """
    删除交易，自动回滚科目余额。
    """
    transaction = db.get(Transaction, guid)
    if transaction is None:
        raise ValueError(f"交易 {guid} 不存在，无法删除")

    now = datetime.utcnow()
    revert_changes: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for split in transaction.splits:
        amount = _split_amount(split)
        revert_changes[split.account_guid] -= amount
    _apply_balance_changes(db, revert_changes, now)

    db.delete(transaction)


def _apply_balance_changes(db: Session, changes: Dict[str, Decimal], timestamp: datetime) -> None:
    """
    根据分录金额增量更新 accounts.current_balance。
    """

    for account_guid, delta in changes.items():
        account = db.get(Account, account_guid)
        if account is None:
            raise ValueError(f"科目 {account_guid} 不存在，无法更新余额")
        current = account.current_balance or Decimal("0")
        account.current_balance = current + delta
        account.updated_at = timestamp


def _split_amount(split: Split) -> Decimal:
    """
    将分录的分数金额还原为 Decimal。
    """
    denominator = split.value_denom or 1
    return Decimal(split.value_num) / Decimal(denominator)

