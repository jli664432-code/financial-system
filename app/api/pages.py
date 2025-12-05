"""
页面路由，提供浏览器界面。
"""
from datetime import date
from calendar import monthrange
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import jinja2
from urllib.parse import quote_plus

from ..crud import account as account_crud
from ..crud import transaction as transaction_crud
from ..crud import financial_report as financial_report_crud
from ..crud import business as business_crud
from ..crud import fixed_expense as fixed_expense_crud
from ..database import get_db
from ..schemas.transaction import SplitCreate, TransactionCreate
from ..schemas import AccountBalanceResponse, TransactionDetailResponse
from ..schemas.fixed_expense import FixedExpenseCreate, FixedExpenseUpdate
from ..schemas.business import (
    BusinessDocumentCreate,
    BusinessDocumentItemCreate,
    BusinessDocumentType,
)
from ..models import CashflowType
from sqlalchemy import select


# 创建支持自动重新加载的 Jinja2 环境
template_dir = str(Path(__file__).resolve().parent.parent / "templates")
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir),
    auto_reload=True,
    autoescape=True
)
# 添加 Python 内置函数到模板环境
jinja_env.globals['float'] = float
jinja_env.globals['hasattr'] = hasattr
jinja_env.globals['str'] = str
jinja_env.globals['abs'] = abs
templates = Jinja2Templates(env=jinja_env)
router = APIRouter(include_in_schema=False)


def _common_context() -> Dict[str, Any]:
    """提供模板公用上下文。"""

    return {"current_year": date.today().year}


def _parse_decimal(value: str, field_label: str) -> Decimal:
    if value is None or value == "":
        raise ValueError(f"{field_label} 不能为空")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:  # noqa: PERF203
        raise ValueError(f"{field_label} 格式不正确") from exc
    if amount <= 0:
        raise ValueError(f"{field_label} 必须大于 0")
    return amount


def _build_fixed_expense_payload(form_data) -> FixedExpenseCreate:
    name = (form_data.get("name") or "").strip()
    if not name:
        raise ValueError("费用名称不能为空")

    amount = _parse_decimal(form_data.get("amount"), "扣款金额")

    expense_account_guid = form_data.get("expense_account_guid")
    primary_account_guid = form_data.get("primary_account_guid")

    if not expense_account_guid:
        raise ValueError("请选择费用科目")
    if not primary_account_guid:
        raise ValueError("请选择优先扣款科目")

    fallback_guid = form_data.get("fallback_account_guid") or None

    day_raw = form_data.get("day_of_month")
    try:
        day_of_month = int(day_raw) if day_raw else 1
    except ValueError as exc:  # noqa: PERF203
        raise ValueError("扣款日格式不正确") from exc
    day_of_month = max(1, min(day_of_month, 28))

    is_active = bool(form_data.get("is_active"))

    return FixedExpenseCreate(
        name=name,
        amount=amount,
        expense_account_guid=expense_account_guid,
        primary_account_guid=primary_account_guid,
        fallback_account_guid=fallback_guid,
        day_of_month=day_of_month,
        is_active=is_active,
    )


def _transaction_form_context(
    request: Request,
    db: Session,
    *,
    mode: str = "edit",
    transaction=None,
    error: str | None = None,
    form_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    构建交易表单页面所需的上下文。
    """

    accounts = account_crud.list_accounts(db)
    accounts_json = [
        {
            "value": account.guid,
            "label": (
                f"{account.code} {account.name}" if account.code else account.name
            ),
        }
        for account in accounts
    ]

    post_date_value = date.today().isoformat()
    num_value = ""
    description_value = ""
    splits_data = [
        {"account_guid": "", "direction": "debit", "amount": "", "memo": ""},
        {"account_guid": "", "direction": "credit", "amount": "", "memo": ""},
    ]
    form_action = ""
    current_mode = mode

    if transaction is not None:
        form_action = f"/transactions/{transaction.guid}/edit"
        post_date_value = transaction.post_date.isoformat()
        num_value = transaction.num or ""
        description_value = transaction.description or ""
        splits_data = []
        for split in transaction.splits:
            amount = split.amount
            direction = "debit" if amount >= 0 else "credit"
            splits_data.append(
                {
                    "account_guid": split.account_guid,
                    "direction": direction,
                    "amount": str(abs(amount)),
                    "memo": split.memo or "",
                }
            )

    if form_state:
        post_date_value = form_state.get("post_date") or post_date_value
        num_value = form_state.get("num") or num_value
        description_value = form_state.get("description") or description_value
        if form_state.get("splits_data"):
            splits_data = form_state["splits_data"]

    context = {
        "request": request,
        "accounts": accounts,
        "accounts_json": accounts_json,
        "form_action": form_action,
        "mode": current_mode if mode is None else mode,
        "post_date_value": post_date_value,
        "num_value": num_value,
        "description_value": description_value,
        "splits_data": splits_data,
        "error": error,
    } | _common_context()

    return context


def _parse_transaction_splits(form_data) -> tuple[List[SplitCreate], List[Dict[str, str]]]:
    """
    从表单数据中解析分录，返回分录对象和用于回填的表单数据。
    """

    splits: List[SplitCreate] = []
    form_view: List[Dict[str, str]] = []

    idx = 0
    found = False
    while True:
        account_key = f"splits_{idx}_account_guid"
        if account_key not in form_data:
            break

        found = True
        account_guid = form_data.get(account_key)
        amount_str = form_data.get(f"splits_{idx}_amount")
        direction = form_data.get(f"splits_{idx}_direction", "debit")
        memo = form_data.get(f"splits_{idx}_memo")

        form_view.append(
            {
                "account_guid": account_guid or "",
                "amount": amount_str or "",
                "direction": direction,
                "memo": memo or "",
            }
        )

        if not account_guid or not amount_str:
            raise ValueError("分录信息不完整，请填写科目和金额")

        try:
            amount = Decimal(amount_str)
        except InvalidOperation as exc:  # noqa: PERF203
            raise ValueError("金额格式不正确，请输入数字") from exc

        if direction == "credit":
            amount = -amount
        elif direction != "debit":
            raise ValueError("分录方向不正确")

        splits.append(
            SplitCreate(
                account_guid=account_guid,
                amount=amount,
                memo=memo or None,
            )
        )
        idx += 1

    if not found or len(splits) < 2:
        raise ValueError("至少需要两条分录")

    total = sum(split.amount for split in splits)
    if total != Decimal("0"):
        raise ValueError("分录借贷不平衡，请检查金额")

    return splits, form_view


@router.get("/")
def home(request: Request) -> Any:
    """主页。"""

    context = {"request": request} | _common_context()
    return templates.TemplateResponse("index.html", context)


@router.get("/accounts/view")
def accounts_page(
    request: Request,
    success: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """会计科目列表页面。"""

    accounts = account_crud.list_accounts(db, include_hidden=True)
    context = {
        "request": request,
        "accounts": accounts,
        "success": success,
        "error": error,
    } | _common_context()
    return templates.TemplateResponse("accounts.html", context)


@router.post("/accounts/manage")
def manage_account(
    request: Request,
    action: str = Form(...),
    account_guid: str | None = Form(None),
    name: str | None = Form(None),
    account_type: str | None = Form(None),
    code: str | None = Form(None),
    parent_guid: str | None = Form(None),
    description: str | None = Form(None),
    hidden: bool = Form(False),
    placeholder: bool = Form(False),
    is_cash: bool = Form(False),
    db: Session = Depends(get_db),
) -> Any:
    """科目管理：创建、更新、删除。"""
    
    try:
        if action == "create":
            if not name or not account_type:
                return RedirectResponse(
                    "/accounts/view?error=" + "科目名称和类型不能为空",
                    status_code=303
                )
            
            account_crud.create_account(
                db,
                name=name,
                account_type=account_type,
                code=code if code else None,
                parent_guid=parent_guid if parent_guid else None,
                description=description if description else None,
                hidden=hidden,
                placeholder=placeholder,
                is_cash=is_cash,
            )
            db.commit()
            return RedirectResponse(
                "/accounts/view?success=" + f"科目 '{name}' 创建成功",
                status_code=303
            )
        
        elif action == "update":
            if not account_guid:
                return RedirectResponse(
                    "/accounts/view?error=" + "科目ID不能为空",
                    status_code=303
                )
            
            account_crud.update_account(
                db,
                guid=account_guid,
                name=name,
                account_type=account_type,
                code=code if code else None,
                parent_guid=parent_guid if parent_guid else None,
                description=description if description else None,
                hidden=hidden,
                placeholder=placeholder,
                is_cash=is_cash,
            )
            db.commit()
            return RedirectResponse(
                "/accounts/view?success=" + f"科目更新成功",
                status_code=303
            )
        
        elif action == "delete":
            if not account_guid:
                return RedirectResponse(
                    "/accounts/view?error=" + "科目ID不能为空",
                    status_code=303
                )
            
            account_crud.delete_account(db, account_guid)
            db.commit()
            return RedirectResponse(
                "/accounts/view?success=" + "科目删除成功",
                status_code=303
            )
        
        else:
            return RedirectResponse(
                "/accounts/view?error=" + "无效的操作",
                status_code=303
            )
    
    except ValueError as e:
        db.rollback()
        return RedirectResponse(
            f"/accounts/view?error={str(e)}",
            status_code=303
        )
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            f"/accounts/view?error=操作失败：{str(e)}",
            status_code=303
        )


@router.get("/transactions/view")
def transactions_page(
    request: Request,
    db: Session = Depends(get_db),
    success: str | None = None,
    error: str | None = None,
) -> Any:
    """交易列表页面。"""

    transactions = transaction_crud.list_transactions(db, limit=50)
    context = {
        "request": request,
        "transactions": transactions,
        "success_message": success,
        "error_message": error,
    } | _common_context()
    return templates.TemplateResponse("transactions.html", context)


@router.get("/transactions/{tx_guid}/edit")
def transaction_edit_form(
    tx_guid: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """渲染交易编辑表单。"""

    transaction = transaction_crud.get_transaction(db, tx_guid)
    if transaction is None:
        raise HTTPException(status_code=404, detail="未找到对应交易")

    context = _transaction_form_context(
        request,
        db,
        mode="edit",
        transaction=transaction,
    )
    return templates.TemplateResponse("transaction_new.html", context)


@router.post("/transactions/{tx_guid}/edit")
async def transaction_edit_submit(
    tx_guid: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """处理交易编辑提交。"""

    transaction = transaction_crud.get_transaction(db, tx_guid)
    if transaction is None:
        raise HTTPException(status_code=404, detail="未找到对应交易")

    form_data = await request.form()
    try:
        splits, form_view = _parse_transaction_splits(form_data)
        post_date = form_data.get("post_date")
        if not post_date:
            raise ValueError("记账日期不能为空")

        data = TransactionCreate(
            post_date=date.fromisoformat(post_date),
            description=form_data.get("description") or None,
            num=form_data.get("num") or None,
            splits=splits,
        )
        transaction_crud.update_transaction(db, tx_guid, data)
    except Exception as exc:  # noqa: BLE001
        context = _transaction_form_context(
            request,
            db,
            mode="edit",
            transaction=transaction,
            error=str(exc),
            form_state={
                "post_date": form_data.get("post_date"),
                "num": form_data.get("num"),
                "description": form_data.get("description"),
                "splits_data": form_view if "form_view" in locals() else None,
            },
        )
        return templates.TemplateResponse("transaction_new.html", context)

    success_msg = quote_plus("交易已更新")
    return RedirectResponse(
        url=f"/transactions/view?success={success_msg}",
        status_code=303,
    )


@router.post("/transactions/{tx_guid}/delete")
def transaction_delete(
    tx_guid: str,
    db: Session = Depends(get_db),
) -> Any:
    """删除交易。"""

    try:
        transaction_crud.delete_transaction(db, tx_guid)
        success_msg = quote_plus("交易已删除")
        return RedirectResponse(
            url=f"/transactions/view?success={success_msg}", status_code=303
        )
    except ValueError as exc:
        error_msg = quote_plus(str(exc))
        return RedirectResponse(
            url=f"/transactions/view?error={error_msg}",
            status_code=303,
        )


@router.get("/reports/balances")
def balances_report_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """科目余额报表页面。"""

    balances = []
    debug_info = None
    error_msg = None
    
    try:
        # 尝试查询数据
        rows = account_crud.list_account_balances(db)
        
        if not rows:
            # 如果没有数据，直接返回空列表
            context = {
                "request": request,
                "balances": [],
                "error": None,
                "debug_info": None,
            } | _common_context()
            return templates.TemplateResponse("reports_balances.html", context)
        
        # 处理每一行数据
        for row in rows:
            try:
                row_dict = dict(row)
                # 先进行字段映射（视图返回的是 name 和 guid，不是 account_name 和 account_guid）
                mapped_data = {
                    "account_guid": row_dict.get("account_guid") or row_dict.get("guid", ""),
                    "account_name": row_dict.get("account_name") or row_dict.get("name", "-"),
                    "account_type": row_dict.get("account_type", "-"),
                    "balance": row_dict.get("balance", 0),
                }
                # 尝试使用 Pydantic 模型验证
                try:
                    validated = AccountBalanceResponse.model_validate(mapped_data)
                    balances.append(validated.model_dump())
                except Exception as val_exc:  # noqa: BLE001
                    # 如果验证失败，直接使用映射后的数据
                    balances.append(mapped_data)
                    # 记录调试信息（只在第一次失败时）
                    if debug_info is None:
                        debug_info = {
                            "validation_error": str(val_exc),
                            "actual_fields": list(row_dict.keys()),
                            "sample_data": {k: str(v)[:50] for k, v in list(row_dict.items())[:5]}
                        }
            except Exception as dict_exc:  # noqa: BLE001
                # 如果转换为字典失败，记录错误
                if debug_info is None:
                    debug_info = {
                        "dict_error": str(dict_exc),
                        "row_type": str(type(row)),
                    }
    except Exception as exc:  # noqa: BLE001
        # 如果查询失败，记录详细错误信息
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"查询失败：{str(exc)}"
        debug_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "traceback": error_trace.split('\n')[-5:],  # 只显示最后5行
        }
    
    context = {
        "request": request,
        "balances": balances,
        "error": error_msg,
        "debug_info": debug_info,
    } | _common_context()
    return templates.TemplateResponse("reports_balances.html", context)


@router.get("/reports/transaction-details")
def transaction_details_report_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """交易明细报表页面。"""

    details = []
    debug_info = None
    error_msg = None
    
    try:
        # 尝试查询数据
        rows = transaction_crud.list_transaction_details(db, limit=100)
        
        if not rows:
            # 如果没有数据，直接返回空列表
            context = {
                "request": request,
                "details": [],
                "error": None,
                "debug_info": None,
            } | _common_context()
            return templates.TemplateResponse("reports_transaction_details.html", context)
        
        # 处理每一行数据
        for row in rows:
            try:
                row_dict = dict(row)
                # 先进行字段映射（视图没有 account_guid，需要从其他字段获取或使用 split_guid）
                # 根据调试信息，视图有 account_code 和 account_name，但没有 account_guid
                # 我们可以使用 split_guid 作为 account_guid 的替代，或者设为空字符串
                mapped_data = {
                    "tx_guid": row_dict.get("tx_guid", ""),
                    "post_date": row_dict.get("post_date"),
                    "account_guid": row_dict.get("account_guid") or row_dict.get("split_guid", ""),  # 使用 split_guid 作为备选
                    "account_name": row_dict.get("account_name", "-"),
                    "amount": row_dict.get("amount", 0),
                    "memo": row_dict.get("memo"),
                    "description": row_dict.get("description"),
                }
                # 尝试使用 Pydantic 模型验证
                try:
                    validated = TransactionDetailResponse.model_validate(mapped_data)
                    details.append(validated.model_dump())
                except Exception as val_exc:  # noqa: BLE001
                    # 如果验证失败，直接使用映射后的数据
                    details.append(mapped_data)
                    # 记录调试信息（只在第一次失败时）
                    if debug_info is None:
                        debug_info = {
                            "validation_error": str(val_exc),
                            "actual_fields": list(row_dict.keys()),
                            "sample_data": {k: str(v)[:50] for k, v in list(row_dict.items())[:5]}
                        }
            except Exception as dict_exc:  # noqa: BLE001
                # 如果转换为字典失败，记录错误
                if debug_info is None:
                    debug_info = {
                        "dict_error": str(dict_exc),
                        "row_type": str(type(row)),
                    }
    except Exception as exc:  # noqa: BLE001
        # 如果查询失败，记录详细错误信息
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"查询失败：{str(exc)}"
        debug_info = {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "traceback": error_trace.split('\n')[-10:],  # 显示最后10行
        }
    
    context = {
        "request": request,
        "details": details,
        "error": error_msg,
        "debug_info": debug_info,
    } | _common_context()
    return templates.TemplateResponse("reports_transaction_details.html", context)


@router.get("/reports/financial")
def financial_report_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """会计报表页面（展示上一完整月份的快照）。"""

    balance_sheet = None
    income_statement = None
    cashflow_statement = None
    report_month = None
    error_msg = None

    try:
        report_month, reports = financial_report_crud.get_or_create_monthly_reports(db)
        balance_sheet = reports.get("balance_sheet")
        income_statement = reports.get("income_statement")
        cashflow_statement = reports.get("cashflow_statement")
    except Exception as exc:  # noqa: BLE001
        error_msg = f"生成或加载月度报表失败：{exc}"
        import traceback

        traceback.print_exc()

    context = {
        "request": request,
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "cashflow_statement": cashflow_statement,
        "report_month_label": report_month.strftime("%Y年%m月") if report_month else None,
        "error": error_msg,
        "is_current_report": False,
    } | _common_context()
    return templates.TemplateResponse("reports_financial.html", context)


@router.get("/reports/financial/current")
def current_financial_report_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """快速生成当前日期的会计报表（不保存）。"""

    balance_sheet = None
    income_statement = None
    cashflow_statement = None
    error_msg = None
    today = date.today()

    try:
        # 直接生成当前日期的报表，不保存到数据库
        balance_sheet = financial_report_crud.generate_balance_sheet(
            db, 
            report_date=today
        )
        
        # 利润表和现金流量表使用年初至今的数据
        year_start = date(today.year, 1, 1)
        income_statement = financial_report_crud.generate_income_statement(
            db,
            start_date=year_start,
            end_date=today,
        )
        
        cashflow_statement = financial_report_crud.generate_cashflow_statement(
            db,
            start_date=year_start,
            end_date=today,
        )
    except Exception as exc:  # noqa: BLE001
        error_msg = f"生成当前报表失败：{exc}"
        import traceback

        traceback.print_exc()

    context = {
        "request": request,
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "cashflow_statement": cashflow_statement,
        "report_month_label": f"{today.strftime('%Y年%m月%d日')}（当前实时报表）",
        "error": error_msg,
        "is_current_report": True,
    } | _common_context()
    return templates.TemplateResponse("reports_financial.html", context)


@router.get("/fixed-expenses")
def fixed_expenses_page(
    request: Request,
    db: Session = Depends(get_db),
    success: str | None = None,
    error: str | None = None,
    warning: str | None = None,
    edit_id: Optional[int] = None,
) -> Any:
    """固定费用配置页面。"""

    expenses = fixed_expense_crud.list_fixed_expenses(db)
    accounts = account_crud.list_accounts(db, include_hidden=True)
    today = date.today()
    rows = []
    for expense in expenses:
        max_day = monthrange(today.year, today.month)[1]
        due_day = max(1, min(expense.day_of_month, max_day))
        due_date = date(today.year, today.month, due_day)
        rows.append(
            {
                "expense": expense,
                "due_date": due_date,
                "is_due": fixed_expense_crud.is_due(expense, today),
            }
        )

    editing_expense = None
    if edit_id:
        for row in rows:
            if row["expense"].id == edit_id:
                editing_expense = row["expense"]
                break

    context = {
        "request": request,
        "accounts": accounts,
        "fixed_expense_rows": rows,
        "editing_expense": editing_expense,
        "success": success,
        "error": error,
        "warning": warning,
    } | _common_context()
    return templates.TemplateResponse("fixed_expenses.html", context)


@router.post("/fixed-expenses/manage")
async def fixed_expenses_manage(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    处理固定费用的新增、更新、删除。
    """

    form_data = await request.form()
    action = form_data.get("action", "create")

    try:
        if action == "delete":
            expense_id = form_data.get("expense_id")
            if not expense_id:
                raise ValueError("缺少固定费用 ID，无法删除。")
            fixed_expense_crud.delete_fixed_expense(db, int(expense_id))
            db.commit()
            msg = quote_plus("固定费用已删除")
            return RedirectResponse(f"/fixed-expenses?success={msg}", status_code=303)

        payload = _build_fixed_expense_payload(form_data)

        if action == "update":
            expense_id = form_data.get("expense_id")
            if not expense_id:
                raise ValueError("缺少固定费用 ID，无法更新。")
            fixed_expense_crud.update_fixed_expense(
                db,
                int(expense_id),
                FixedExpenseUpdate(**payload.model_dump()),
            )
            db.commit()
            msg = quote_plus(f"固定费用「{payload.name}」已更新")
            return RedirectResponse(f"/fixed-expenses?success={msg}", status_code=303)

        # 默认执行创建
        fixed_expense_crud.create_fixed_expense(db, payload)
        db.commit()
        msg = quote_plus(f"固定费用「{payload.name}」已创建")
        return RedirectResponse(f"/fixed-expenses?success={msg}", status_code=303)

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        error_msg = quote_plus(str(exc))
        edit_id = form_data.get("expense_id") or ""
        suffix = f"&edit_id={edit_id}" if edit_id else ""
        return RedirectResponse(
            f"/fixed-expenses?error={error_msg}{suffix}",
            status_code=303,
        )


@router.post("/fixed-expenses/run")
async def fixed_expenses_run(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    执行固定费用扣款。
    """

    form_data = await request.form()
    action = form_data.get("action", "single")
    run_date_str = form_data.get("run_date")
    try:
        run_date_value = (
            date.fromisoformat(run_date_str) if run_date_str else date.today()
        )
    except ValueError:
        run_date_value = date.today()

    try:
        if action == "all":
            results = fixed_expense_crud.execute_all_due_fixed_expenses(
                db, run_date=run_date_value
            )
            db.commit()
            if not results:
                warn = quote_plus("本月暂无到期的固定费用，未执行。")
                return RedirectResponse(f"/fixed-expenses?warning={warn}", status_code=303)

            success_count = len([item for item in results if item[1]])
            success_msg = quote_plus(
                f"本次共执行 {len(results)} 项固定费用，成功 {success_count} 项。"
            )
            warning_parts: List[str] = []
            for expense, _, warnings in results:
                if warnings:
                    warning_parts.append(
                        f"{expense.name}：{'；'.join(warnings)}"
                    )

            redirect_url = f"/fixed-expenses?success={success_msg}"
            if warning_parts:
                warning_msg = quote_plus(" / ".join(warning_parts))
                redirect_url += f"&warning={warning_msg}"
            return RedirectResponse(redirect_url, status_code=303)

        # 默认执行单个
        expense_id = form_data.get("expense_id")
        if not expense_id:
            raise ValueError("缺少固定费用 ID，无法执行扣费。")
        expense = fixed_expense_crud.get_fixed_expense(db, int(expense_id))
        if expense is None:
            raise ValueError("固定费用不存在。")

        tx_guid, warnings = fixed_expense_crud.execute_fixed_expense(
            db,
            expense,
            run_date=run_date_value,
            force=True,
        )
        db.commit()

        if tx_guid is None:
            detail = "；".join(warnings) if warnings else "扣费失败"
            raise ValueError(detail)

        success_msg = quote_plus(
            f"已执行 {expense.name} 的扣费，生成交易 {tx_guid}"
        )
        redirect_url = f"/fixed-expenses?success={success_msg}"
        if warnings:
            redirect_url += f"&warning={quote_plus('；'.join(warnings))}"
        return RedirectResponse(redirect_url, status_code=303)

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        error_msg = quote_plus(str(exc))
        return RedirectResponse(f"/fixed-expenses?error={error_msg}", status_code=303)


# ============================================================
# 业务流程相关页面
# ============================================================

@router.get("/business/list")
def business_list_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """业务单据列表页面。"""
    # 注意：这里需要查询业务单据，但当前没有查询接口，暂时返回空列表
    # 后续可以添加查询业务单据的 CRUD 函数
    documents = []
    context = {
        "request": request,
        "documents": documents,
        "error": None,
    } | _common_context()
    return templates.TemplateResponse("business_list.html", context)


def _get_business_form_context(
    request: Request,
    db: Session,
    doc_type: str,
    doc_type_name: str,
    doc_type_desc: str,
    show_cashflow: bool = False,
) -> Dict[str, Any]:
    """获取业务流程表单的通用上下文。"""
    accounts = account_crud.list_accounts(db)
    cashflow_types = []
    if show_cashflow:
        stmt = select(CashflowType).where(CashflowType.is_active.is_(True)).order_by(CashflowType.sort_order, CashflowType.id)
        cashflow_types = list(db.scalars(stmt).all())
    
    return {
        "request": request,
        "accounts": accounts,
        "cashflow_types": cashflow_types,
        "today": date.today().isoformat(),
        "doc_type": doc_type,
        "doc_type_name": doc_type_name,
        "doc_type_desc": doc_type_desc,
        "show_cashflow": show_cashflow,
        "error": None,
        "success": False,
    } | _common_context()


@router.get("/business/sales/new")
def sales_form_page(
    request: Request,
    db: Session = Depends(get_db),
    success: int | None = 0,
) -> Any:
    """创建销售单表单页面。"""
    context = _get_business_form_context(
        request, db, "SALE", "创建销售业务单据", "销售商品给客户，自动生成会计凭证", show_cashflow=True
    )
    context["success"] = bool(success)
    return templates.TemplateResponse("business_form.html", context)


@router.post("/business/sales/new")
async def sales_form_submit(
    request: Request,
    db: Session = Depends(get_db),
    doc_no: str | None = Form(None),
    doc_date: str = Form(...),
    partner_name: str | None = Form(None),
    reference_no: str | None = Form(None),
    description: str | None = Form(None),
    cashflow_type_id: int | None = Form(None),
) -> Any:
    """处理销售单表单提交。"""
    context = _get_business_form_context(
        request, db, "SALE", "创建销售业务单据", "销售商品给客户，自动生成会计凭证", show_cashflow=True
    )
    
    try:
        # 解析表单数据
        form_data = await request.form()
        items = []
        item_index = 0
        
        while f"items_{item_index}_debit_account_guid" in form_data:
            debit_guid = form_data.get(f"items_{item_index}_debit_account_guid")
            credit_guid = form_data.get(f"items_{item_index}_credit_account_guid")
            amount_str = form_data.get(f"items_{item_index}_amount")
            item_desc = form_data.get(f"items_{item_index}_description")
            item_memo = form_data.get(f"items_{item_index}_memo")
            item_cf_id = form_data.get(f"items_{item_index}_cashflow_type_id")
            
            if debit_guid and credit_guid and amount_str:
                items.append(BusinessDocumentItemCreate(
                    debit_account_guid=debit_guid,
                    credit_account_guid=credit_guid,
                    amount=Decimal(amount_str),
                    description=item_desc or None,
                    memo=item_memo or None,
                    cashflow_type_id=int(item_cf_id) if item_cf_id else None,
                ))
            item_index += 1
        
        if not items:
            raise ValueError("至少需要一条明细")
        
        data = BusinessDocumentCreate(
            doc_no=doc_no or None,
            doc_date=date.fromisoformat(doc_date),
            partner_name=partner_name or None,
            reference_no=reference_no or None,
            description=description or None,
            cashflow_type_id=int(cashflow_type_id) if cashflow_type_id else None,
            items=items,
        )
        
        document = business_crud.create_business_document(db, data, BusinessDocumentType.SALE)
        # 成功后重定向到成功页面或列表
        return RedirectResponse(url=f"/business/sales/new?success=1", status_code=303)
    except Exception as exc:
        context["error"] = str(exc)
        return templates.TemplateResponse("business_form.html", context)


@router.get("/business/purchases/new")
def purchase_form_page(
    request: Request,
    db: Session = Depends(get_db),
    success: int | None = 0,
) -> Any:
    """创建采购单表单页面。"""
    context = _get_business_form_context(
        request, db, "PURCHASE", "创建采购业务单据", "从供应商采购商品，自动生成会计凭证"
    )
    context["success"] = bool(success)
    return templates.TemplateResponse("business_form.html", context)


@router.post("/business/purchases/new")
async def purchase_form_submit(
    request: Request,
    db: Session = Depends(get_db),
    doc_no: str | None = Form(None),
    doc_date: str = Form(...),
    partner_name: str | None = Form(None),
    reference_no: str | None = Form(None),
    description: str | None = Form(None),
    cashflow_type_id: int | None = Form(None),
) -> Any:
    """处理采购单表单提交。"""
    context = _get_business_form_context(
        request, db, "PURCHASE", "创建采购业务单据", "从供应商采购商品，自动生成会计凭证"
    )
    
    try:
        form_data = await request.form()
        items = []
        item_index = 0
        
        while f"items_{item_index}_debit_account_guid" in form_data:
            debit_guid = form_data.get(f"items_{item_index}_debit_account_guid")
            credit_guid = form_data.get(f"items_{item_index}_credit_account_guid")
            amount_str = form_data.get(f"items_{item_index}_amount")
            item_desc = form_data.get(f"items_{item_index}_description")
            item_memo = form_data.get(f"items_{item_index}_memo")
            item_cf_id = form_data.get(f"items_{item_index}_cashflow_type_id")
            
            if debit_guid and credit_guid and amount_str:
                items.append(BusinessDocumentItemCreate(
                    debit_account_guid=debit_guid,
                    credit_account_guid=credit_guid,
                    amount=Decimal(amount_str),
                    description=item_desc or None,
                    memo=item_memo or None,
                    cashflow_type_id=int(item_cf_id) if item_cf_id else None,
                ))
            item_index += 1
        
        if not items:
            raise ValueError("至少需要一条明细")
        
        data = BusinessDocumentCreate(
            doc_no=doc_no or None,
            doc_date=date.fromisoformat(doc_date),
            partner_name=partner_name or None,
            reference_no=reference_no or None,
            description=description or None,
            cashflow_type_id=int(cashflow_type_id) if cashflow_type_id else None,
            items=items,
        )
        
        business_crud.create_business_document(db, data, BusinessDocumentType.PURCHASE)
        return RedirectResponse(url=f"/business/purchases/new?success=1", status_code=303)
    except Exception as exc:
        context["error"] = str(exc)
        return templates.TemplateResponse("business_form.html", context)


@router.get("/business/expenses/new")
def expense_form_page(
    request: Request,
    db: Session = Depends(get_db),
    success: int | None = 0,
) -> Any:
    """创建费用单表单页面。"""
    context = _get_business_form_context(
        request, db, "EXPENSE", "创建费用报销单", "员工报销费用，自动生成会计凭证", show_cashflow=True
    )
    context["success"] = bool(success)
    return templates.TemplateResponse("business_form.html", context)


@router.post("/business/expenses/new")
async def expense_form_submit(
    request: Request,
    db: Session = Depends(get_db),
    doc_no: str | None = Form(None),
    doc_date: str = Form(...),
    partner_name: str | None = Form(None),
    reference_no: str | None = Form(None),
    description: str | None = Form(None),
    cashflow_type_id: int | None = Form(None),
) -> Any:
    """处理费用单表单提交。"""
    context = _get_business_form_context(
        request, db, "EXPENSE", "创建费用报销单", "员工报销费用，自动生成会计凭证", show_cashflow=True
    )
    
    try:
        form_data = await request.form()
        items = []
        item_index = 0
        
        while f"items_{item_index}_debit_account_guid" in form_data:
            debit_guid = form_data.get(f"items_{item_index}_debit_account_guid")
            credit_guid = form_data.get(f"items_{item_index}_credit_account_guid")
            amount_str = form_data.get(f"items_{item_index}_amount")
            item_desc = form_data.get(f"items_{item_index}_description")
            item_memo = form_data.get(f"items_{item_index}_memo")
            item_cf_id = form_data.get(f"items_{item_index}_cashflow_type_id")
            
            if debit_guid and credit_guid and amount_str:
                items.append(BusinessDocumentItemCreate(
                    debit_account_guid=debit_guid,
                    credit_account_guid=credit_guid,
                    amount=Decimal(amount_str),
                    description=item_desc or None,
                    memo=item_memo or None,
                    cashflow_type_id=int(item_cf_id) if item_cf_id else None,
                ))
            item_index += 1
        
        if not items:
            raise ValueError("至少需要一条明细")
        
        data = BusinessDocumentCreate(
            doc_no=doc_no or None,
            doc_date=date.fromisoformat(doc_date),
            partner_name=partner_name or None,
            reference_no=reference_no or None,
            description=description or None,
            cashflow_type_id=int(cashflow_type_id) if cashflow_type_id else None,
            items=items,
        )
        
        business_crud.create_business_document(db, data, BusinessDocumentType.EXPENSE)
        return RedirectResponse(url=f"/business/expenses/new?success=1", status_code=303)
    except Exception as exc:
        context["error"] = str(exc)
        return templates.TemplateResponse("business_form.html", context)


@router.get("/business/cashflow/new")
def cashflow_form_page(
    request: Request,
    db: Session = Depends(get_db),
    success: int | None = 0,
) -> Any:
    """创建收付款单表单页面。"""
    context = _get_business_form_context(
        request, db, "CASHFLOW", "创建收付款业务单据", "记录收款或付款，自动生成会计凭证", show_cashflow=True
    )
    context["success"] = bool(success)
    return templates.TemplateResponse("business_form.html", context)


@router.post("/business/cashflow/new")
async def cashflow_form_submit(
    request: Request,
    db: Session = Depends(get_db),
    doc_no: str | None = Form(None),
    doc_date: str = Form(...),
    partner_name: str | None = Form(None),
    reference_no: str | None = Form(None),
    description: str | None = Form(None),
    cashflow_type_id: int | None = Form(None),
) -> Any:
    """处理收付款单表单提交。"""
    context = _get_business_form_context(
        request, db, "CASHFLOW", "创建收付款业务单据", "记录收款或付款，自动生成会计凭证", show_cashflow=True
    )
    
    # 收付款业务必须选择现金流量分类
    if not cashflow_type_id:
        context["error"] = "收付款业务必须选择现金流量分类"
        return templates.TemplateResponse("business_form.html", context)
    
    try:
        form_data = await request.form()
        items = []
        item_index = 0
        
        while f"items_{item_index}_debit_account_guid" in form_data:
            debit_guid = form_data.get(f"items_{item_index}_debit_account_guid")
            credit_guid = form_data.get(f"items_{item_index}_credit_account_guid")
            amount_str = form_data.get(f"items_{item_index}_amount")
            item_desc = form_data.get(f"items_{item_index}_description")
            item_memo = form_data.get(f"items_{item_index}_memo")
            item_cf_id = form_data.get(f"items_{item_index}_cashflow_type_id")
            
            if debit_guid and credit_guid and amount_str:
                items.append(BusinessDocumentItemCreate(
                    debit_account_guid=debit_guid,
                    credit_account_guid=credit_guid,
                    amount=Decimal(amount_str),
                    description=item_desc or None,
                    memo=item_memo or None,
                    cashflow_type_id=int(item_cf_id) if item_cf_id else None,
                ))
            item_index += 1
        
        if not items:
            raise ValueError("至少需要一条明细")
        
        data = BusinessDocumentCreate(
            doc_no=doc_no or None,
            doc_date=date.fromisoformat(doc_date),
            partner_name=partner_name or None,
            reference_no=reference_no or None,
            description=description or None,
            cashflow_type_id=int(cashflow_type_id) if cashflow_type_id else None,
            items=items,
        )
        
        business_crud.create_business_document(db, data, BusinessDocumentType.CASHFLOW)
        return RedirectResponse(url=f"/business/cashflow/new?success=1", status_code=303)
    except Exception as exc:
        context["error"] = str(exc)
        return templates.TemplateResponse("business_form.html", context)


