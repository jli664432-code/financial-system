"""
账户相关的数据库操作。
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Account, v_account_balance
from ..utils.guid_helper import generate_guid


def list_accounts(db: Session, include_hidden: bool = False) -> List[Account]:
    """
    查询会计科目。
    
    Args:
        db: 数据库会话
        include_hidden: 是否包含隐藏的科目
    """
    stmt = select(Account)
    if not include_hidden:
        stmt = stmt.where(Account.hidden.is_(False))
    stmt = stmt.order_by(Account.code, Account.name)
    return list(db.scalars(stmt).all())


def get_account(db: Session, guid: str) -> Optional[Account]:
    """
    根据主键获取科目。
    """
    return db.get(Account, guid)


def create_account(
    db: Session,
    name: str,
    account_type: str,
    code: Optional[str] = None,
    parent_guid: Optional[str] = None,
    description: Optional[str] = None,
    hidden: bool = False,
    placeholder: bool = False,
    is_cash: bool = False,
) -> Account:
    """
    创建新科目。
    """
    # 检查科目名称是否已存在
    stmt = select(Account).where(Account.name == name)
    existing = db.scalar(stmt)
    if existing:
        raise ValueError(f"科目名称 '{name}' 已存在")
    
    # 如果指定了父科目，验证父科目存在
    if parent_guid:
        parent = db.get(Account, parent_guid)
        if not parent:
            raise ValueError(f"父科目不存在：{parent_guid}")
    
    now = datetime.utcnow()
    account = Account(
        guid=generate_guid(),
        name=name,
        account_type=account_type,
        code=code,
        parent_guid=parent_guid,
        description=description,
        hidden=hidden,
        placeholder=placeholder,
        is_cash=is_cash,
        current_balance=0,
        created_at=now,
        updated_at=now,
    )
    db.add(account)
    return account


def update_account(
    db: Session,
    guid: str,
    name: Optional[str] = None,
    account_type: Optional[str] = None,
    code: Optional[str] = None,
    parent_guid: Optional[str] = None,
    description: Optional[str] = None,
    hidden: Optional[bool] = None,
    placeholder: Optional[bool] = None,
    is_cash: Optional[bool] = None,
) -> Account:
    """
    更新科目信息。
    """
    account = db.get(Account, guid)
    if not account:
        raise ValueError(f"科目不存在：{guid}")
    
    # 如果修改名称，检查是否与其他科目冲突
    if name and name != account.name:
        stmt = select(Account).where(Account.name == name, Account.guid != guid)
        existing = db.scalar(stmt)
        if existing:
            raise ValueError(f"科目名称 '{name}' 已存在")
        account.name = name
    
    # 如果指定了父科目，验证父科目存在且不是自己
    if parent_guid is not None:
        if parent_guid == guid:
            raise ValueError("科目不能将自己设为父科目")
        if parent_guid:
            parent = db.get(Account, parent_guid)
            if not parent:
                raise ValueError(f"父科目不存在：{parent_guid}")
        account.parent_guid = parent_guid
    
    if account_type is not None:
        account.account_type = account_type
    if code is not None:
        account.code = code
    if description is not None:
        account.description = description
    if hidden is not None:
        account.hidden = hidden
    if placeholder is not None:
        account.placeholder = placeholder
    if is_cash is not None:
        account.is_cash = is_cash
    
    account.updated_at = datetime.utcnow()
    return account


def delete_account(db: Session, guid: str) -> bool:
    """
    删除科目。
    
    注意：如果科目有子科目或已被使用，不能删除。
    """
    account = db.get(Account, guid)
    if not account:
        raise ValueError(f"科目不存在：{guid}")
    
    # 检查是否有子科目
    stmt = select(Account).where(Account.parent_guid == guid)
    children = db.scalars(stmt).all()
    if children:
        child_names = [c.name for c in children]
        raise ValueError(f"科目有子科目，不能删除。子科目：{', '.join(child_names)}")
    
    # 检查是否已被使用（有余额或有关联的分录）
    if account.current_balance != 0:
        raise ValueError(f"科目余额不为0（当前余额：{account.current_balance}），不能删除")
    
    # 检查是否有关联的分录
    from ..models import Split
    stmt = select(Split).where(Split.account_guid == guid).limit(1)
    has_splits = db.scalar(stmt) is not None
    if has_splits:
        raise ValueError("科目已被使用（存在关联的分录），不能删除。建议隐藏科目而不是删除。")
    
    db.delete(account)
    return True


def list_account_balances(db: Session):
    """
    查询账户余额视图。
    """
    stmt = select(v_account_balance)
    # 尝试按 account_name 排序，如果字段不存在则跳过排序
    try:
        # 直接尝试访问字段，如果不存在会抛出 AttributeError
        stmt = stmt.order_by(v_account_balance.c.account_name)
    except (AttributeError, KeyError):
        # 如果 account_name 不存在，尝试其他可能的字段名
        try:
            stmt = stmt.order_by(v_account_balance.c.name)
        except (AttributeError, KeyError):
            try:
                stmt = stmt.order_by(v_account_balance.c.account_guid)
            except (AttributeError, KeyError):
                # 如果所有字段都不存在，不排序
                pass
    except Exception:  # noqa: BLE001
        # 如果排序失败，直接返回不排序的结果
        pass
    return db.execute(stmt).mappings().all()

