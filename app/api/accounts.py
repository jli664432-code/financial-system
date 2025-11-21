"""
账户相关的 API 路由。
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import account as account_crud
from ..database import get_db
from ..schemas.account import (
    AccountResponse,
    AccountCreate,
    AccountUpdate,
)
from ..schemas import AccountBalanceResponse

router = APIRouter(prefix="/accounts", tags=["会计科目"])


@router.get("/", response_model=List[AccountResponse])
def read_accounts(
    include_hidden: bool = False,
    db: Session = Depends(get_db),
) -> List[AccountResponse]:
    """
    查询会计科目。
    
    Args:
        include_hidden: 是否包含隐藏的科目
    """
    accounts = account_crud.list_accounts(db, include_hidden=include_hidden)
    return [AccountResponse.model_validate(item, from_attributes=True) for item in accounts]


@router.get("/{account_guid}", response_model=AccountResponse)
def read_account(account_guid: str, db: Session = Depends(get_db)) -> AccountResponse:
    """
    根据 guid 查询单个科目。
    """
    account = account_crud.get_account(db, account_guid)
    if account is None:
        raise HTTPException(status_code=404, detail="未找到对应科目")
    return AccountResponse.model_validate(account, from_attributes=True)


@router.post("/", response_model=AccountResponse, status_code=201)
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    创建新科目。
    """
    try:
        account = account_crud.create_account(
            db,
            name=data.name,
            account_type=data.account_type,
            code=data.code,
            parent_guid=data.parent_guid,
            description=data.description,
            hidden=data.hidden,
            placeholder=data.placeholder,
            is_cash=data.is_cash,
        )
        db.flush()
        return AccountResponse.model_validate(account, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{account_guid}", response_model=AccountResponse)
def update_account(
    account_guid: str,
    data: AccountUpdate,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    更新科目信息。
    """
    try:
        account = account_crud.update_account(
            db,
            guid=account_guid,
            name=data.name,
            account_type=data.account_type,
            code=data.code,
            parent_guid=data.parent_guid,
            description=data.description,
            hidden=data.hidden,
            placeholder=data.placeholder,
            is_cash=data.is_cash,
        )
        db.flush()
        return AccountResponse.model_validate(account, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{account_guid}", status_code=204)
def delete_account(
    account_guid: str,
    db: Session = Depends(get_db),
):
    """
    删除科目。
    
    注意：如果科目有子科目、余额不为0或已被使用，不能删除。
    """
    try:
        account_crud.delete_account(db, account_guid)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/balances/", response_model=List[AccountBalanceResponse], tags=["报表"])
def read_account_balances(db: Session = Depends(get_db)):
    """
    调用数据库视图 `v_account_balance`，查看每个科目的余额。
    """
    rows = account_crud.list_account_balances(db)
    return [AccountBalanceResponse.model_validate(row) for row in rows]

