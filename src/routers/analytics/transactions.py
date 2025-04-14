from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, List, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.dependencies import get_current_user
from src.config import TIME_FRAMES
from src.models import Budget, Transaction, TransactionType, User
from src.schemas.analytics_schemas import (
    BudgetCategoryStat,
    BudgetOverview,
    CategoryStat,
    IncomeExpenseComparison,
    LineChartResponse,
    LinePoint,
    MonthComparison,
    PaymentStat,
    PieChartResponse,
    SummaryResponse,
    TotalSpent,
)
from src.utils.analytics_helper import (
    calculate_percent,
    get_all_transactions_for_user,
    round_decimal,
)

router = APIRouter(prefix="/transactions", tags=["Transaction Analytics"])

from decimal import Decimal


@router.get("/summary")
async def get_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: TransactionType | None = None,
) -> SummaryResponse:
    """
    📊 Общая аналитика всех транзакций (ручных и банковских):
    - Суммы за неделю / месяц / год
    - Топ 5 категорий
    - Процент от бюджета
    """
    now = datetime.now(UTC)
    start_of_week = datetime(now.year, now.month, now.day - now.weekday(), tzinfo=UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)
    start_of_year = datetime(now.year, 1, 1, tzinfo=UTC)

    # ✅ Загружаем все транзакции (объединённые)
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="User ID is missing")
    all_transactions: list[dict[str, Any]] = await get_all_transactions_for_user(current_user.id)

    # 🔍 Фильтрация по типу
    if transaction_type:
        all_transactions = [t for t in all_transactions if t["type"] == transaction_type]

    # 🗓️ Разделение по времени
    week_txns = [t for t in all_transactions if t["date"] >= start_of_week]
    month_txns = [t for t in all_transactions if t["date"] >= start_of_month]
    year_txns = [t for t in all_transactions if t["date"] >= start_of_year]

    # 💵 Подсчёт сумм
    week_total = sum(Decimal(str(cast(float, t["amount"]))) for t in week_txns)
    month_total = sum(Decimal(str(cast(float, t["amount"]))) for t in month_txns)
    year_total = sum(Decimal(str(cast(float, t["amount"]))) for t in year_txns)

    # 🏷️ Категории
    categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in all_transactions:
        if t["category"]:
            categories[t["category"]] += Decimal(str(cast(float, t["amount"])))

    total_amount = sum(categories.values())
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]

    # 💳 Способы оплаты (только для ручных)
    payment_methods: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in all_transactions:
        if t["source"] == "manual" and t.get("payment_method"):
            payment_methods[t["payment_method"]] += Decimal(str(cast(float, t["amount"])))

    total_payments = sum(payment_methods.values())

    return SummaryResponse(
        total_spent=TotalSpent(
            week=round_decimal(Decimal(str(week_total))),
            month=round_decimal(Decimal(str(month_total))),
            year=round_decimal(Decimal(str(year_total))),
        ),
        top_categories=[
            CategoryStat(
                category=cat,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, Decimal(str(total_amount)))
                if total_amount > Decimal("0")
                else Decimal("0"),
            )
            for cat, amount in top_categories
        ],
        payment_methods=[
            PaymentStat(
                method=method,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, Decimal(str(total_payments)))
                if total_payments > Decimal("0")
                else Decimal("0"),
            )
            for method, amount in payment_methods.items()
        ],
    )


@router.get("/pie")
async def get_pie_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: TransactionType | None = None,
) -> PieChartResponse:
    """
    🥧 Круговая диаграмма по категориям за текущий месяц
    """
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="User ID is missing")

    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Получаем все транзакции
    all_transactions = await get_all_transactions_for_user(current_user.id)

    # Фильтрация по дате и типу
    filtered = [
        t
        for t in all_transactions
        if t["date"] >= start_of_month
        and (transaction_type is None or t["type"] == transaction_type)
    ]

    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transactions found for this month",
        )

    # Группировка по категориям
    categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total: Decimal = Decimal("0")

    for t in filtered:
        if t["category"]:
            amount = Decimal(str(cast(float, t["amount"])))
            categories[t["category"]] += amount
            total += amount

    return PieChartResponse(
        data=[
            CategoryStat(
                category=cat,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total),
            )
            for cat, amount in categories.items()
        ]
    )


@router.get("/line")
async def get_line_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    timeframe: Literal["day", "week", "month", "year"] = "month",
    transaction_type: TransactionType | None = None,
) -> LineChartResponse:
    """
    📈 Линейный график по дням:
    - Поддержка фильтра по типу (доход / расход)
    - Поддержка timeframe: day, week, month, year
    """
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="User ID is missing")

    now = datetime.now(UTC)
    days = TIME_FRAMES[timeframe]
    start_date = now - timedelta(days=days)

    # Загружаем все транзакции
    all_transactions = await get_all_transactions_for_user(current_user.id)

    # Фильтрация по дате и типу
    filtered = [
        t
        for t in all_transactions
        if t["date"] >= start_date and (transaction_type is None or t["type"] == transaction_type)
    ]

    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transactions found for the last {days} days",
        )

    # Группировка по дате
    by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in filtered:
        tx_date = t["date"].date()
        by_date[tx_date] += Decimal(str(cast(float, t["amount"])))

    # Заполнение пропущенных дней
    all_dates: list[date] = []
    current = start_date.date()
    while current <= now.date():
        all_dates.append(current)
        current += timedelta(days=1)

    return LineChartResponse(
        timeframe=timeframe,
        data=[
            LinePoint(
                date=d,
                amount=round_decimal(by_date.get(d, Decimal("0"))),
            )
            for d in all_dates
        ],
    )


@router.get("/compare")
async def compare_months(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: TransactionType | None = None,
) -> MonthComparison:
    """
    🔄 Сравнение текущего и предыдущего месяца
    """
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="User ID is missing")

    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Предыдущий месяц
    if now.month == 1:
        prev_month = 12
        prev_year = now.year - 1
    else:
        prev_month = now.month - 1
        prev_year = now.year

    start_of_prev_month = datetime(prev_year, prev_month, 1, tzinfo=UTC)
    end_of_prev_month = start_of_month - timedelta(days=1)

    # Все транзакции
    all_transactions = await get_all_transactions_for_user(current_user.id)

    # Фильтрация по типу
    if transaction_type:
        all_transactions = [t for t in all_transactions if t["type"] == transaction_type]

    # Группировка по месяцам
    current_month_txns = [t for t in all_transactions if t["date"] >= start_of_month]
    prev_month_txns = [
        t for t in all_transactions if start_of_prev_month <= t["date"] <= end_of_prev_month
    ]

    # Суммы
    current_total = Decimal(
        str(sum(Decimal(str(cast(float, t["amount"]))) for t in current_month_txns))
    )
    prev_total = Decimal(str(sum(Decimal(str(cast(float, t["amount"]))) for t in prev_month_txns)))

    return MonthComparison(
        previous_month_total=round_decimal(prev_total),
        current_month_total=round_decimal(current_total),
        change_percent=calculate_percent(current_total - prev_total, prev_total)
        if prev_total > Decimal("0")
        else Decimal("0"),
    )


@router.get("/budget-analysis")
async def get_budget_analysis(
    current_user: Annotated[User, Depends(get_current_user)],
) -> BudgetOverview:
    """
    💰 Анализ бюджета по категориям на основе всех расходов (ручных и банковских)
    """
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="User ID is missing")

    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Загружаем все транзакции (ручные + plaid)
    all_txns = await get_all_transactions_for_user(current_user.id)

    # Фильтруем только расходы текущего месяца
    expenses = [t for t in all_txns if t["type"] == "expense" and t["date"] >= start_of_month]

    # Загружаем бюджеты
    budgets = await Budget.find(Budget.user_id == current_user.id).to_list()
    if not budgets:
        raise HTTPException(status_code=404, detail="No budgets found")

    # Группировка расходов по категориям
    expenses_by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in expenses:
        if t["category"]:
            expenses_by_category[t["category"]] += Decimal(str(cast(float, t["amount"])))

    # Ответ
    stats: list[BudgetCategoryStat] = []
    for budget in budgets:
        spent = expenses_by_category.get(budget.category, Decimal("0"))
        percent = calculate_percent(spent, budget.limit) if budget.limit > 0 else Decimal("0")

        stats.append(
            BudgetCategoryStat(
                category=budget.category,
                budget=round_decimal(budget.limit),
                spent=round_decimal(spent),
                percent=percent,
            )
        )

    return BudgetOverview(categories=stats)


@router.get("/compare-types")
async def compare_types(
    current_user: Annotated[User, Depends(get_current_user)],
    timeframe: Literal["week", "month", "year"] = "month",
) -> IncomeExpenseComparison:
    """
    🔄 Сравнение доходов и расходов
    """
    now = datetime.now(UTC)
    days = TIME_FRAMES[timeframe]
    start_date = now - timedelta(days=days)

    # Получаем все транзакции за период
    transactions = await Transaction.find(
        Transaction.user_id == current_user.id, Transaction.date >= start_date
    ).to_list()

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transactions found for the last {days} days",
        )

    # Группируем по типам
    expenses = [t for t in transactions if t.type == TransactionType.EXPENSE]
    incomes = [t for t in transactions if t.type == TransactionType.INCOME]

    # Считаем суммы
    expenses_total = sum(t.amount for t in expenses)
    incomes_total = sum(t.amount for t in incomes)

    # Группируем по категориям
    expense_categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    income_categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for t in expenses:
        if t.category:
            expense_categories[t.category] += t.amount

    for t in incomes:
        if t.category:
            income_categories[t.category] += t.amount

    # Формируем ответ
    return IncomeExpenseComparison(
        timeframe=timeframe,
        total_income=round_decimal(Decimal(str(incomes_total))),
        total_expense=round_decimal(Decimal(str(expenses_total))),
        difference=round_decimal(Decimal(str(incomes_total - expenses_total))),
        income_percent=calculate_percent(
            Decimal(str(incomes_total)), Decimal(str(incomes_total + expenses_total))
        ),
        expense_percent=calculate_percent(
            Decimal(str(expenses_total)), Decimal(str(incomes_total + expenses_total))
        ),
        top_income_categories=[
            CategoryStat(
                category=cat,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, Decimal(str(incomes_total))),
            )
            for cat, amount in income_categories.items()
        ],
        top_expense_categories=[
            CategoryStat(
                category=cat,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, Decimal(str(expenses_total))),
            )
            for cat, amount in expense_categories.items()
        ],
    )
