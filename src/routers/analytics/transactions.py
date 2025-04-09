from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.dependencies import get_current_user
from src.config import TIME_FRAMES
from src.models import Budget, Transaction, User
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
    TransactionType,
)
from src.utils.analytics_helper import calculate_percent, round_decimal

router = APIRouter(prefix="/transactions", tags=["Transaction Analytics"])


@router.get("/summary")
async def get_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: Annotated[Optional[TransactionType], Query(None)] = None,
) -> SummaryResponse:
    """
    📊 Общая аналитика транзакций:
    - Суммы за неделю / месяц / год
    - Топ 5 категорий
    - Процент от бюджета
    """
    now = datetime.now(UTC)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)
    start_of_year = datetime(now.year, 1, 1, tzinfo=UTC)

    # Базовый запрос для текущего пользователя
    query = Transaction.find(Transaction.user_id == current_user.id)

    # Добавляем фильтр по типу, если он указан
    if transaction_type:
        query = query.find(Transaction.type == transaction_type)

    # Получаем все транзакции
    all_transactions = await query.to_list()

    # Фильтруем транзакции по периодам
    week_transactions = [t for t in all_transactions if t.date >= start_of_week]
    month_transactions = [t for t in all_transactions if t.date >= start_of_month]
    year_transactions = [t for t in all_transactions if t.date >= start_of_year]

    # Считаем суммы
    week_total = sum(t.amount for t in week_transactions)
    month_total = sum(t.amount for t in month_transactions)
    year_total = sum(t.amount for t in year_transactions)

    # Группируем по категориям
    categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in all_transactions:
        if t.category:
            categories[t.category] += t.amount

    # Сортируем категории по сумме
    sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]

    # Считаем общую сумму для расчета процентов
    total_amount = sum(amount for amount in categories.values())

    # Группируем по способам оплаты
    payment_methods: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in all_transactions:
        if t.payment_method:
            payment_methods[t.payment_method] += t.amount

    # Считаем общую сумму для способов оплаты
    total_payments = sum(amount for amount in payment_methods.values())

    # Формируем ответ
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
                if total_amount > 0
                else Decimal("0"),
            )
            for cat, amount in sorted_categories
        ],
        payment_methods=[
            PaymentStat(
                method=method,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, Decimal(str(total_payments)))
                if total_payments > 0
                else Decimal("0"),
            )
            for method, amount in payment_methods.items()
        ],
    )


@router.get("/pie")
async def get_pie_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: Annotated[Optional[TransactionType], Query(None)] = None,
) -> PieChartResponse:
    """
    🥧 Круговая диаграмма расходов по категориям
    """
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Базовый запрос для текущего пользователя
    query = Transaction.find(Transaction.user_id == current_user.id)

    # Добавляем фильтр по типу, если он указан
    if transaction_type:
        query = query.find(Transaction.type == transaction_type)

    # Добавляем фильтр по дате (текущий месяц)
    query = query.find(Transaction.date >= start_of_month)

    # Получаем транзакции
    transactions = await query.to_list()

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transactions found for this month",
        )

    # Группируем по категориям
    categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total: Decimal = Decimal("0")

    for t in transactions:
        if t.category:
            categories[t.category] += t.amount
            total += t.amount

    # Формируем ответ
    return PieChartResponse(
        data=[
            CategoryStat(
                category=cat,
                amount=round_decimal(Decimal(str(amount))),
                percent=calculate_percent(Decimal(str(amount)), Decimal(str(total))),
            )
            for cat, amount in categories.items()
        ]
    )


@router.get("/line")
async def get_line_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    timeframe: Literal["day", "week", "month", "year"] = "month",
    transaction_type: Annotated[Optional[TransactionType], Query(None)] = None,
) -> LineChartResponse:
    """
    📈 Линейный график расходов по времени
    """
    now = datetime.now(UTC)
    days = TIME_FRAMES[timeframe]

    # Базовый запрос для текущего пользователя
    query = Transaction.find(Transaction.user_id == current_user.id)

    # Добавляем фильтр по типу, если он указан
    if transaction_type:
        query = query.find(Transaction.type == transaction_type)

    # Добавляем фильтр по дате
    start_date = now - timedelta(days=days)
    query = query.find(Transaction.date >= start_date)

    # Получаем транзакции
    transactions = await query.to_list()

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transactions found for the last {days} days",
        )

    # Группируем по датам
    by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for t in transactions:
        t_date = t.date.date()
        by_date[t_date] += t.amount

    # Заполняем пропуски нулями
    all_dates: list[date] = []
    current = start_date.date()
    while current <= now.date():
        all_dates.append(current)
        current += timedelta(days=1)

    # Формируем ответ
    return LineChartResponse(
        timeframe=timeframe,
        data=[
            LinePoint(date=d, amount=round_decimal(Decimal(str(by_date.get(d, Decimal("0"))))))
            for d in all_dates
        ],
    )


@router.get("/compare")
async def compare_months(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: Annotated[Optional[TransactionType], Query(None)] = None,
) -> MonthComparison:
    """
    🔄 Сравнение текущего месяца с предыдущим
    """
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Определяем начало предыдущего месяца
    if now.month == 1:
        prev_month = 12
        prev_year = now.year - 1
    else:
        prev_month = now.month - 1
        prev_year = now.year

    start_of_prev_month = datetime(prev_year, prev_month, 1, tzinfo=UTC)

    # Если текущий месяц - январь, то предыдущий - декабрь прошлого года
    if now.month == 1:
        end_of_prev_month = datetime(now.year, 1, 1, tzinfo=UTC) - timedelta(days=1)
    else:
        end_of_prev_month = start_of_month - timedelta(days=1)

    # Базовый запрос для текущего пользователя
    query = Transaction.find(Transaction.user_id == current_user.id)

    # Добавляем фильтр по типу, если он указан
    if transaction_type:
        query = query.find(Transaction.type == transaction_type)

    # Получаем все транзакции
    all_transactions = await query.to_list()

    # Фильтруем транзакции по месяцам
    current_month_transactions = [t for t in all_transactions if t.date >= start_of_month]
    prev_month_transactions = [
        t for t in all_transactions if start_of_prev_month <= t.date <= end_of_prev_month
    ]

    # Считаем суммы
    current_month_total = sum(t.amount for t in current_month_transactions)
    prev_month_total = sum(t.amount for t in prev_month_transactions)

    # Группируем по категориям
    current_categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    prev_categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for t in current_month_transactions:
        if t.category:
            current_categories[t.category] += t.amount

    for t in prev_month_transactions:
        if t.category:
            prev_categories[t.category] += t.amount

    # Формируем ответ
    return MonthComparison(
        previous_month_total=round_decimal(Decimal(str(prev_month_total))),
        current_month_total=round_decimal(Decimal(str(current_month_total))),
        change_percent=calculate_percent(
            Decimal(str(current_month_total - prev_month_total)), Decimal(str(prev_month_total))
        )
        if prev_month_total > 0
        else Decimal("0"),
    )


@router.get("/budget-analysis")
async def get_budget_analysis(
    current_user: Annotated[User, Depends(get_current_user)],
) -> BudgetOverview:
    """
    💰 Анализ бюджета по категориям
    """
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Получаем все бюджеты пользователя
    budgets = await Budget.find(Budget.user_id == current_user.id).to_list()

    if not budgets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No budgets found",
        )

    # Получаем расходы за текущий месяц
    expenses = await Transaction.find(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.date >= start_of_month,
    ).to_list()

    # Группируем расходы по категориям
    expenses_by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for expense in expenses:
        if expense.category:
            expenses_by_category[expense.category] += expense.amount

    # Формируем ответ
    budget_stats: list[BudgetCategoryStat] = []
    for budget in budgets:
        spent = expenses_by_category.get(budget.category, Decimal("0"))
        percent = calculate_percent(spent, budget.limit) if budget.limit > 0 else Decimal("0")

        budget_stats.append(
            BudgetCategoryStat(
                category=budget.category,
                budget=round_decimal(budget.limit),
                spent=round_decimal(spent),
                percent=percent,
            )
        )

    return BudgetOverview(categories=budget_stats)


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
    expenses = [t for t in transactions if t.type == "expense"]
    incomes = [t for t in transactions if t.type == "income"]

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
