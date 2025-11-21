"""
业务流程相关的 API。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import business as business_crud
from ..database import get_db
from ..schemas.business import (
    BusinessDocumentResponse,
    BusinessDocumentType,
    CashflowDocumentCreate,
    ExpenseDocumentCreate,
    PurchaseDocumentCreate,
    SalesDocumentCreate,
)

router = APIRouter(prefix="/business", tags=["业务流程"])


def _create_document(
    db: Session,
    data,
    doc_type: BusinessDocumentType,
) -> BusinessDocumentResponse:
    try:
        document = business_crud.create_business_document(db, data, doc_type)
        db.flush()  # 确保对象有 ID
    except ValueError as exc:  # 输入校验错误
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # 其他错误（数据库错误、模型错误等）
        db.rollback()
        import traceback
        error_detail = f"{type(exc).__name__}: {str(exc)}"
        # 在开发环境下显示完整错误信息
        import sys
        if sys.stderr.isatty():  # 如果是开发环境
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_detail) from exc

    try:
        return BusinessDocumentResponse.model_validate(document, from_attributes=True)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"数据序列化错误: {str(exc)}"
        ) from exc


@router.post(
    "/sales",
    response_model=BusinessDocumentResponse,
    status_code=201,
    summary="创建销售业务单据",
)
def create_sales_document(
    data: SalesDocumentCreate,
    db: Session = Depends(get_db),
) -> BusinessDocumentResponse:
    return _create_document(db, data, BusinessDocumentType.SALE)


@router.post(
    "/purchases",
    response_model=BusinessDocumentResponse,
    status_code=201,
    summary="创建采购业务单据",
)
def create_purchase_document(
    data: PurchaseDocumentCreate,
    db: Session = Depends(get_db),
) -> BusinessDocumentResponse:
    return _create_document(db, data, BusinessDocumentType.PURCHASE)


@router.post(
    "/expenses",
    response_model=BusinessDocumentResponse,
    status_code=201,
    summary="创建费用报销单",
)
def create_expense_document(
    data: ExpenseDocumentCreate,
    db: Session = Depends(get_db),
) -> BusinessDocumentResponse:
    return _create_document(db, data, BusinessDocumentType.EXPENSE)


@router.post(
    "/cashflow",
    response_model=BusinessDocumentResponse,
    status_code=201,
    summary="创建收付款业务单据",
)
def create_cashflow_document(
    data: CashflowDocumentCreate,
    db: Session = Depends(get_db),
) -> BusinessDocumentResponse:
    return _create_document(db, data, BusinessDocumentType.CASHFLOW)


