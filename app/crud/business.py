"""
业务流程相关的数据库操作。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Set

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    Account,
    BusinessDocument,
    BusinessDocumentItem,
    CashflowType,
)
from ..schemas.business import (
    BusinessDocumentCreate,
    BusinessDocumentItemCreate,
    BusinessDocumentType,
)
from ..schemas.transaction import SplitCreate, TransactionCreate
from .transaction import create_transaction


def create_business_document(
    db: Session,
    data: BusinessDocumentCreate,
    doc_type: BusinessDocumentType,
) -> BusinessDocument:
    """
    创建业务单据并自动生成会计凭证与分录。
    """

    now = datetime.utcnow()
    account_map = _load_accounts(db, _collect_account_guids(data.items))
    _ensure_cashflow_types(db, _collect_cashflow_type_ids(data))

    # 如果 doc_no 为空，自动生成单据编号
    doc_no = data.doc_no if data.doc_no and data.doc_no.strip() else _generate_doc_no(db, doc_type, data.doc_date)

    split_inputs = _build_splits(data, doc_type, account_map)

    tx_description = data.description or f"{doc_type.value} 单据"
    tx_data = TransactionCreate(
        num=doc_no,
        post_date=data.doc_date,
        description=tx_description,
        business_type=doc_type.value,
        reference_no=data.reference_no,
        splits=split_inputs,
    )
    transaction = create_transaction(db, tx_data)

    document = BusinessDocument(
        doc_type=doc_type.value,
        doc_no=doc_no,
        doc_date=data.doc_date,
        partner_name=data.partner_name,
        reference_no=data.reference_no or transaction.reference_no,
        description=data.description,
        currency=data.currency,
        total_amount=_calc_total_amount(data.items),
        status="POSTED",
        transaction_guid=transaction.guid,
        created_at=now,
        updated_at=now,
    )
    document.items = _build_items(data.items, data.cashflow_type_id)

    db.add(document)
    return document


def _build_items(
    items: List[BusinessDocumentItemCreate],
    default_cashflow_type_id: int | None,
) -> List[BusinessDocumentItem]:
    rows: List[BusinessDocumentItem] = []
    for idx, item in enumerate(items, start=1):
        row = BusinessDocumentItem(
            line_no=item.line_no or idx,
            description=item.description,
            memo=item.memo,
            debit_account_guid=item.debit_account_guid,
            credit_account_guid=item.credit_account_guid,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=item.amount,
            cashflow_type_id=item.cashflow_type_id or default_cashflow_type_id,
        )
        rows.append(row)
    return rows


def _build_splits(
    data: BusinessDocumentCreate,
    doc_type: BusinessDocumentType,
    account_map: Dict[str, Account],
) -> List[SplitCreate]:
    split_inputs: List[SplitCreate] = []
    for item in data.items:
        memo = item.memo or data.description or f"{doc_type.value} 明细"
        debit_account = account_map[item.debit_account_guid]
        credit_account = account_map[item.credit_account_guid]
        item_cashflow_id = item.cashflow_type_id or data.cashflow_type_id

        debit_split = SplitCreate(
            account_guid=item.debit_account_guid,
            amount=item.amount,
            memo=memo,
            cashflow_type_id=_resolve_cashflow_type_id(
                debit_account,
                item_cashflow_id,
            ),
        )
        credit_split = SplitCreate(
            account_guid=item.credit_account_guid,
            amount=-item.amount,
            memo=memo,
            cashflow_type_id=_resolve_cashflow_type_id(
                credit_account,
                item_cashflow_id,
            ),
        )
        split_inputs.extend([debit_split, credit_split])
    return split_inputs


def _resolve_cashflow_type_id(account: Account, candidate_id: int | None) -> int | None:
    """
    仅对现金/银行科目强制要求现金流量分类。
    """

    if account.is_cash:
        if candidate_id is None:
            raise ValueError(f"现金/银行科目 {account.name} 需要指定现金流量分类")
        return candidate_id
    return candidate_id


def _load_accounts(db: Session, account_guids: Set[str]) -> Dict[str, Account]:
    if not account_guids:
        raise ValueError("没有需要匹配的会计科目")

    stmt = select(Account).where(Account.guid.in_(account_guids))
    accounts = {account.guid: account for account in db.scalars(stmt).all()}
    missing = account_guids - accounts.keys()
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"以下科目不存在：{missing_list}")
    return accounts


def _collect_account_guids(items: Iterable[BusinessDocumentItemCreate]) -> Set[str]:
    guids: Set[str] = set()
    for item in items:
        guids.add(item.debit_account_guid)
        guids.add(item.credit_account_guid)
    return guids


def _collect_cashflow_type_ids(data: BusinessDocumentCreate) -> Set[int]:
    ids: Set[int] = set()
    if data.cashflow_type_id:
        ids.add(data.cashflow_type_id)
    for item in data.items:
        if item.cashflow_type_id:
            ids.add(item.cashflow_type_id)
    return ids


def _ensure_cashflow_types(db: Session, ids: Set[int]) -> None:
    if not ids:
        return
    stmt = select(CashflowType.id).where(CashflowType.id.in_(ids))
    existing = {row for row in db.scalars(stmt).all()}
    missing = ids - existing
    if missing:
        missing_list = ", ".join(str(item) for item in sorted(missing))
        raise ValueError(f"以下现金流量分类不存在：{missing_list}")


def _calc_total_amount(items: Iterable[BusinessDocumentItemCreate]) -> Decimal:
    total = Decimal("0")
    for item in items:
        total += item.amount
    return total


def _generate_doc_no(
    db: Session,
    doc_type: BusinessDocumentType,
    doc_date: date,
) -> str:
    """
    自动生成单据编号，格式：类型-日期-序号
    例如：SALE-20251120-001
    """
    # 类型前缀映射
    type_prefix = {
        BusinessDocumentType.SALE: "XS",  # 销售
        BusinessDocumentType.PURCHASE: "CG",  # 采购
        BusinessDocumentType.EXPENSE: "FY",  # 费用
        BusinessDocumentType.CASHFLOW: "SF",  # 收付
    }
    prefix = type_prefix.get(doc_type, "DOC")
    
    # 日期格式：YYYYMMDD
    date_str = doc_date.strftime("%Y%m%d")
    
    # 查询当天同类型单据的数量
    stmt = select(func.count(BusinessDocument.id)).where(
        BusinessDocument.doc_type == doc_type.value,
        BusinessDocument.doc_date == doc_date,
    )
    count = db.scalar(stmt) or 0
    
    # 生成序号（从001开始）
    seq = count + 1
    seq_str = f"{seq:03d}"
    
    return f"{prefix}-{date_str}-{seq_str}"


