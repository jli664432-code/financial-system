"""
会计报表相关的数据库操作。
重新设计的报表系统，支持日期范围查询、科目层级汇总、现金流量表等。
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm import Session

from ..models import (
    Account,
    Split,
    Transaction,
    CashflowType,
    v_account_balance,
    v_transaction_detail,
)
from .monthly_report import get_reports_for_month, replace_reports


# 科目类型分类配置
ACCOUNT_TYPE_MAPPING = {
    # 资产类
    "ASSET": "asset",
    "CURRENT_ASSET": "asset",
    "FIXED_ASSET": "asset",
    "NON_CURRENT_ASSET": "asset",
    "CASH": "asset",
    "BANK": "asset",
    "RECEIVABLE": "asset",
    "INVENTORY": "asset",
    # 负债类
    "LIABILITY": "liability",
    "CURRENT_LIABILITY": "liability",
    "NON_CURRENT_LIABILITY": "liability",
    "PAYABLE": "liability",
    # 所有者权益类
    "EQUITY": "equity",
    "CAPITAL": "equity",
    "RETAINED_EARNINGS": "equity",
    # 收入类
    "INCOME": "revenue",
    "REVENUE": "revenue",
    "SALES": "revenue",
    # 费用类
    "EXPENSE": "expense",
    "COST": "expense",
    "OPERATING_EXPENSE": "expense",
    "COGS": "expense",  # 销售成本
}


def _classify_account_type(account_type: str) -> Optional[str]:
    """将科目类型分类到报表类别。"""
    account_type_upper = account_type.upper()
    return ACCOUNT_TYPE_MAPPING.get(account_type_upper)


def _get_account_tree(db: Session) -> Dict[str, Dict]:
    """构建科目树结构，用于层级汇总。"""
    stmt = select(Account).where(Account.hidden == False)
    accounts = db.scalars(stmt).all()
    
    account_dict = {}
    root_accounts = []
    
    # 第一遍：建立索引
    for account in accounts:
        account_dict[account.guid] = {
            "account": account,
            "children": [],
            "level": 0,
        }
    
    # 第二遍：建立父子关系
    for account in accounts:
        if account.parent_guid and account.parent_guid in account_dict:
            account_dict[account.parent_guid]["children"].append(account.guid)
            account_dict[account.guid]["level"] = account_dict[account.parent_guid]["level"] + 1
        else:
            root_accounts.append(account.guid)
    
    return {
        "accounts": account_dict,
        "roots": root_accounts,
    }


def _calculate_balance_at_date(
    db: Session,
    account_guid: str,
    report_date: date,
) -> Decimal:
    """计算指定日期时点的科目余额。"""
    # 查询该科目在指定日期之前的所有分录
    stmt = (
        select(func.sum(Split.value_num / Split.value_denom))
        .join(Transaction)
        .where(
            and_(
                Split.account_guid == account_guid,
                Transaction.post_date <= report_date,
            )
        )
    )
    result = db.scalar(stmt)
    return Decimal(str(result or 0))


def _calculate_period_amount(
    db: Session,
    account_guid: str,
    start_date: date,
    end_date: date,
) -> Decimal:
    """计算指定期间内的科目发生额。"""
    # 查询该科目在指定期间内的所有分录
    stmt = (
        select(func.sum(Split.value_num / Split.value_denom))
        .join(Transaction)
        .where(
            and_(
                Split.account_guid == account_guid,
                Transaction.post_date >= start_date,
                Transaction.post_date <= end_date,
            )
        )
    )
    result = db.scalar(stmt)
    return Decimal(str(result or 0))


def generate_balance_sheet(
    db: Session,
    report_date: Optional[date] = None,
    include_children: bool = True,
) -> Dict:
    """
    生成资产负债表数据。
    
    Args:
        db: 数据库会话
        report_date: 报表日期（可选，默认使用当前日期）
        include_children: 是否包含子科目汇总
    
    Returns:
        包含资产、负债、所有者权益的字典
    """
    if report_date is None:
        report_date = date.today()
    
    # 查询所有科目
    stmt = select(Account).where(Account.hidden == False)
    accounts = db.scalars(stmt).all()
    
    # 初始化报表数据
    assets = []  # 资产
    liabilities = []  # 负债
    equity = []  # 所有者权益
    
    asset_total = Decimal("0")
    liability_total = Decimal("0")
    equity_total = Decimal("0")
    
    # 计算净利润（用于平衡检查）
    net_income = Decimal("0")
    
    for account in accounts:
        # 计算该科目在报表日期的余额
        balance = _calculate_balance_at_date(db, account.guid, report_date)
        
        if balance == 0 and not include_children:
            continue
        
        account_type = _classify_account_type(account.account_type)
        
        item = {
            "guid": account.guid,
            "code": account.code or "",
            "name": account.name,
            "balance": balance,
            "account_type": account.account_type,
            "parent_guid": account.parent_guid,
            "is_placeholder": account.placeholder,
        }
        
        # 根据科目类型分类
        if account_type == "asset":
            assets.append(item)
            asset_total += balance
        elif account_type == "liability":
            liabilities.append(item)
            # 负债余额是负数，但显示和计算时应该用绝对值
            liability_total -= balance  # 减去负数等于加上正数
        elif account_type == "equity":
            equity.append(item)
            equity_total -= balance  # 权益余额是负数，但显示和计算时应该用绝对值
        elif account_type == "revenue":
            # 收入余额是负数（贷方），需要取绝对值
            net_income -= balance  # 减去负数等于加上正数
        elif account_type == "expense":
            # 费用余额是正数（借方）
            net_income -= balance  # 减去正数
    
    # 如果包含子科目，进行层级汇总
    if include_children:
        assets = _aggregate_by_level(assets, db, report_date)
        liabilities = _aggregate_by_level(liabilities, db, report_date)
        equity = _aggregate_by_level(equity, db, report_date)
    
    # 净利润应该增加所有者权益（未分配利润）
    equity_with_income = equity_total + net_income
    total_liability_equity = liability_total + equity_with_income
    
    return {
        "report_date": report_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "asset_total": asset_total,
        "liability_total": liability_total,
        "equity_total": equity_total,
        "net_income": net_income,
        "equity_with_income": equity_with_income,
        "total_liability_equity": total_liability_equity,
        "is_balanced": abs(asset_total - total_liability_equity) < Decimal("0.01"),
    }


def _aggregate_by_level(
    items: List[Dict],
    db: Session,
    report_date: date,
) -> List[Dict]:
    """按科目层级汇总余额。"""
    # 构建科目树
    tree = _get_account_tree(db)
    account_dict = tree["accounts"]
    
    # 为每个父科目计算子科目汇总
    parent_totals = {}
    item_guid_set = {item["guid"] for item in items}
    
    for item in items:
        if item["parent_guid"] and item["parent_guid"] in item_guid_set:
            if item["parent_guid"] not in parent_totals:
                parent_totals[item["parent_guid"]] = Decimal("0")
            parent_totals[item["parent_guid"]] += item["balance"]
    
    # 添加父科目汇总项
    aggregated = []
    processed_parents = set()
    
    for item in items:
        aggregated.append(item)
        
        # 如果是父科目且有子科目，添加汇总行
        if item["guid"] in parent_totals and item["guid"] not in processed_parents:
            total = parent_totals[item["guid"]]
            if total != 0:
                aggregated.append({
                    "guid": item["guid"] + "_subtotal",
                    "code": "",
                    "name": f"  └─ {item['name']} 小计",
                    "balance": total,
                    "account_type": item["account_type"],
                    "parent_guid": item["guid"],
                    "is_placeholder": True,
                    "is_subtotal": True,
                })
            processed_parents.add(item["guid"])
    
    return aggregated


def generate_income_statement(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_children: bool = True,
) -> Dict:
    """
    生成利润表数据。
    
    Args:
        db: 数据库会话
        start_date: 开始日期（可选，默认使用年初）
        end_date: 结束日期（可选，默认使用当前日期）
        include_children: 是否包含子科目汇总
    
    Returns:
        包含收入、费用、利润的字典
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = date(end_date.year, 1, 1)  # 默认从年初开始
    
    # 查询所有科目
    stmt = select(Account).where(Account.hidden == False)
    accounts = db.scalars(stmt).all()
    
    # 初始化报表数据
    revenues = []  # 收入
    expenses = []  # 费用
    
    revenue_total = Decimal("0")
    expense_total = Decimal("0")
    
    for account in accounts:
        # 计算该科目在指定期间内的发生额
        period_amount = _calculate_period_amount(db, account.guid, start_date, end_date)
        
        if period_amount == 0 and not include_children:
            continue
        
        account_type = _classify_account_type(account.account_type)
        
        item = {
            "guid": account.guid,
            "code": account.code or "",
            "name": account.name,
            "amount": period_amount,
            "account_type": account.account_type,
            "parent_guid": account.parent_guid,
        }
        
        # 根据科目类型分类
        if account_type == "revenue":
            # 收入发生额：贷方为正（负数），需要取绝对值
            revenues.append(item)
            revenue_total -= period_amount  # 减去负数等于加上正数
        elif account_type == "expense":
            # 费用发生额：借方为正（正数），直接使用
            expenses.append(item)
            expense_total += period_amount
    
    # 如果包含子科目，进行层级汇总
    if include_children:
        revenues = _aggregate_period_by_level(revenues, db, start_date, end_date)
        expenses = _aggregate_period_by_level(expenses, db, start_date, end_date)
    
    # 计算利润：收入 - 费用
    net_income = revenue_total - expense_total
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "revenues": revenues,
        "expenses": expenses,
        "revenue_total": revenue_total,
        "expense_total": expense_total,
        "net_income": net_income,
    }


def _aggregate_period_by_level(
    items: List[Dict],
    db: Session,
    start_date: date,
    end_date: date,
) -> List[Dict]:
    """按科目层级汇总期间发生额。"""
    # 构建科目树
    tree = _get_account_tree(db)
    account_dict = tree["accounts"]
    
    # 为每个父科目计算子科目汇总
    parent_totals = {}
    item_guid_set = {item["guid"] for item in items}
    
    for item in items:
        if item["parent_guid"] and item["parent_guid"] in item_guid_set:
            if item["parent_guid"] not in parent_totals:
                parent_totals[item["parent_guid"]] = Decimal("0")
            parent_totals[item["parent_guid"]] += item["amount"]
    
    # 添加父科目汇总项
    aggregated = []
    processed_parents = set()
    
    for item in items:
        aggregated.append(item)
        
        # 如果是父科目且有子科目，添加汇总行
        if item["guid"] in parent_totals and item["guid"] not in processed_parents:
            total = parent_totals[item["guid"]]
            if total != 0:
                aggregated.append({
                    "guid": item["guid"] + "_subtotal",
                    "code": "",
                    "name": f"  └─ {item['name']} 小计",
                    "amount": total,
                    "account_type": item["account_type"],
                    "parent_guid": item["guid"],
                    "is_subtotal": True,
                })
            processed_parents.add(item["guid"])
    
    return aggregated


def generate_cashflow_statement(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict:
    """
    生成现金流量表数据。
    
    Args:
        db: 数据库会话
        start_date: 开始日期（可选，默认使用年初）
        end_date: 结束日期（可选，默认使用当前日期）
    
    Returns:
        包含经营活动、投资活动、筹资活动现金流量的字典
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = date(end_date.year, 1, 1)  # 默认从年初开始
    
    # 查询所有现金流量分类
    stmt = select(CashflowType).where(
        CashflowType.is_active == True
    ).order_by(CashflowType.sort_order, CashflowType.id)
    cashflow_types = db.scalars(stmt).all()
    
    # 查询指定期间内所有有现金流量分类的分录
    stmt = (
        select(
            CashflowType.flow_type,
            CashflowType.direction,
            CashflowType.name.label("category_name"),
            CashflowType.id.label("cashflow_type_id"),
            func.sum(Split.value_num / Split.value_denom).label("amount"),
        )
        .join(Split, Split.cashflow_type_id == CashflowType.id)
        .join(Transaction, Split.tx_guid == Transaction.guid)
        .where(
            and_(
                Transaction.post_date >= start_date,
                Transaction.post_date <= end_date,
            )
        )
        .group_by(
            CashflowType.flow_type,
            CashflowType.direction,
            CashflowType.name,
            CashflowType.id,
        )
        .order_by(CashflowType.sort_order, CashflowType.id)
    )
    
    rows = db.execute(stmt).mappings().all()
    
    # 分类汇总
    operating_inflow = Decimal("0")  # 经营活动现金流入
    operating_outflow = Decimal("0")  # 经营活动现金流出
    investing_inflow = Decimal("0")  # 投资活动现金流入
    investing_outflow = Decimal("0")  # 投资活动现金流出
    financing_inflow = Decimal("0")  # 筹资活动现金流入
    financing_outflow = Decimal("0")  # 筹资活动现金流出
    
    operating_items = []
    investing_items = []
    financing_items = []
    
    for row in rows:
        amount = Decimal(str(row["amount"] or 0))
        flow_type = row["flow_type"]
        direction = row["direction"]
        category_name = row["category_name"]
        cashflow_type_id = row["cashflow_type_id"]
        
        item = {
            "category_name": category_name,
            "cashflow_type_id": cashflow_type_id,
            "direction": direction,
            "amount": abs(amount),
        }
        
        if flow_type == "OPERATING":
            operating_items.append(item)
            if direction == "INFLOW":
                operating_inflow += abs(amount)
            else:
                operating_outflow += abs(amount)
        elif flow_type == "INVESTING":
            investing_items.append(item)
            if direction == "INFLOW":
                investing_inflow += abs(amount)
            else:
                investing_outflow += abs(amount)
        elif flow_type == "FINANCING":
            financing_items.append(item)
            if direction == "INFLOW":
                financing_inflow += abs(amount)
            else:
                financing_outflow += abs(amount)
    
    # 计算净流量
    operating_net = operating_inflow - operating_outflow
    investing_net = investing_inflow - investing_outflow
    financing_net = financing_inflow - financing_outflow
    total_net = operating_net + investing_net + financing_net
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "operating": {
            "item_list": operating_items,  # 使用 item_list 避免与字典的 items() 方法冲突
            "inflow": operating_inflow,
            "outflow": operating_outflow,
            "net": operating_net,
        },
        "investing": {
            "item_list": investing_items,  # 使用 item_list 避免与字典的 items() 方法冲突
            "inflow": investing_inflow,
            "outflow": investing_outflow,
            "net": investing_net,
        },
        "financing": {
            "item_list": financing_items,  # 使用 item_list 避免与字典的 items() 方法冲突
            "inflow": financing_inflow,
            "outflow": financing_outflow,
            "net": financing_net,
        },
        "total_net": total_net,
    }


def _first_day_of_month(target: date) -> date:
    return target.replace(day=1)


def _last_day_of_month(target: date) -> date:
    first_next_month = (target.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first_next_month - timedelta(days=1)


def _previous_month(today: date) -> date:
    first_day = _first_day_of_month(today)
    prev_month_last_day = first_day - timedelta(days=1)
    return prev_month_last_day.replace(day=1)


def get_or_create_monthly_reports(
    db: Session,
    today: Optional[date] = None,
) -> Tuple[date, Dict[str, Dict]]:
    """
    获取或生成上一整月的报表快照。

    - 始终以“上一整月”为报表月份；
    - 若缓存不存在或月份不符，则重新生成并替换（旧数据自动删除）。
    """

    today = today or date.today()
    target_month = _previous_month(today)

    cached = get_reports_for_month(db, target_month)
    expected_keys = {"balance_sheet", "income_statement", "cashflow_statement"}
    if expected_keys.issubset(cached.keys()):
        return target_month, cached

    month_start = target_month
    month_end = _last_day_of_month(target_month)

    reports = {
        "balance_sheet": generate_balance_sheet(db, report_date=month_end),
        "income_statement": generate_income_statement(
            db,
            start_date=month_start,
            end_date=month_end,
        ),
        "cashflow_statement": generate_cashflow_statement(
            db,
            start_date=month_start,
            end_date=month_end,
        ),
    }

    replace_reports(db, target_month, reports)
    db.commit()

    return target_month, reports
