"""
交易相关的 API 路由。
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..crud import transaction as transaction_crud
from ..database import get_db
from ..schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionDetailResponse,
)

router = APIRouter(prefix="/transactions", tags=["交易"])


@router.get("/", response_model=List[TransactionResponse])
def read_transactions(limit: int = 50, db: Session = Depends(get_db)):
    """
    查询最近的交易记录。
    """
    transactions = transaction_crud.list_transactions(db, limit=limit)
    return [TransactionResponse.model_validate(item, from_attributes=True) for item in transactions]


@router.get("/{tx_guid}", response_model=TransactionResponse)
def read_transaction(tx_guid: str, db: Session = Depends(get_db)):
    """
    根据 guid 查询单笔交易。
    """
    transaction = transaction_crud.get_transaction(db, tx_guid)
    if transaction is None:
        raise HTTPException(status_code=404, detail="未找到对应交易")
    return TransactionResponse.model_validate(transaction, from_attributes=True)


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    """
    新增交易并保存分录。
    """
    transaction = transaction_crud.create_transaction(db, data)
    return TransactionResponse.model_validate(transaction, from_attributes=True)


@router.put("/{tx_guid}", response_model=TransactionResponse)
def update_transaction(
    tx_guid: str,
    data: TransactionCreate,
    db: Session = Depends(get_db),
):
    """
    更新交易。
    """
    try:
        transaction = transaction_crud.update_transaction(db, tx_guid, data)
        return TransactionResponse.model_validate(transaction, from_attributes=True)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "不存在" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.delete("/{tx_guid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(tx_guid: str, db: Session = Depends(get_db)):
    """
    删除交易。
    """
    try:
        transaction_crud.delete_transaction(db, tx_guid)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "不存在" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/details/", response_model=List[TransactionDetailResponse], tags=["报表"])
def read_transaction_details(tx_guid: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    """
    查询交易明细视图 `v_transaction_detail`，可通过 `tx_guid` 精确到单笔交易。
    """
    rows = transaction_crud.list_transaction_details(db, tx_guid=tx_guid, limit=limit)
    return [TransactionDetailResponse.model_validate(row) for row in rows]

