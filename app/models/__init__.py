"""
数据库模型包。

将常用模型对象集中导出，便于其他模块直接引用。
"""
from sqlalchemy import Table

from ..database import Base, engine
from .account import Account
from .transaction import Transaction
from .split import Split
from .cashflow_type import CashflowType
from .business_document import BusinessDocument, BusinessDocumentItem
from .monthly_report import MonthlyReport
from .fixed_expense import FixedExpense

# 读取数据库中的只读视图，用于生成报表数据。
v_account_balance = Table(
    "v_account_balance",
    Base.metadata,
    autoload_with=engine,
)

v_transaction_detail = Table(
    "v_transaction_detail",
    Base.metadata,
    autoload_with=engine,
)

__all__ = [
    "Account",
    "Transaction",
    "Split",
    "CashflowType",
    "BusinessDocument",
    "BusinessDocumentItem",
    "MonthlyReport",
    "FixedExpense",
    "v_account_balance",
    "v_transaction_detail",
]

