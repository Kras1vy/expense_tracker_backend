from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, List, Literal

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.config import TIME_FRAMES
from src.models import Budget, Expense, User
from src.schemas.analytics_schemas import (
    BudgetCategoryStat,
    BudgetOverview,
    CategoryStat,
    LineChartResponse,
    LinePoint,
    MonthComparison,
    PaymentStat,
    PieChartResponse,
    SummaryResponse,
    TotalSpent,
)
from src.utils.analytics_helper import calculate_percent, round_decimal

router = APIRouter(prefix="/expenses", tags=["Expense Analytics"])


@router.get("/summary")
async def get_summary(current_user: Annotated[User, Depends(get_current_user)]) -> SummaryResponse:
    """
    📊 Общая аналитика расходов:
    - Суммы за неделю / месяц / год
    - Топ 5 категорий
    - Распределение по методам оплаты
    """
    # Получаем текущую дату и время
    now = datetime.now(UTC)

    # Вычисляем начальные даты для разных периодов
    start_of_week = now - timedelta(days=now.weekday())
    start_of_month = now.replace(day=1)
    start_of_year = now.replace(month=1, day=1)

    # Получаем все расходы пользователя
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()

    # Инициализируем счетчики для разных периодов
    total_week = total_month = total_year = total_all = Decimal("0")

    # Словари для группировки по категориям и методам оплаты
    by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_payment: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    # Считаем суммы по периодам и категориям
    for expense in expenses:
        # Общая сумма
        total_all += expense.amount

        # Суммы по периодам
        if expense.date >= start_of_year:
            total_year += expense.amount
        if expense.date >= start_of_month:
            total_month += expense.amount
        if expense.date >= start_of_week:
            total_week += expense.amount

        # Группируем по категориям и методам оплаты
        if expense.category:
            by_category[expense.category] += expense.amount
        if expense.payment_method:
            by_payment[expense.payment_method] += expense.amount

    # Получаем топ-5 категорий по расходам
    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]

    # Формируем ответ
    return SummaryResponse(
        total_spent=TotalSpent(
            week=round_decimal(total_week),
            month=round_decimal(total_month),
            year=round_decimal(total_year),
        ),
        top_categories=[
            CategoryStat(
                category=category,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total_all),
            )
            for category, amount in top_categories
        ],
        payment_methods=[
            PaymentStat(
                method=method,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total_all),
            )
            for method, amount in by_payment.items()
        ],
    )


@router.get("/pie")
async def get_pie_chart(
    current_user: Annotated[User, Depends(get_current_user)],
) -> PieChartResponse:
    """🥧 Диаграмма расходов по категориям"""
    # Получаем все расходы пользователя
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()

    # Инициализируем счетчики
    total = Decimal("0")
    by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    # Считаем общую сумму и суммы по категориям
    for expense in expenses:
        if expense.category:
            by_category[expense.category] += expense.amount
            total += expense.amount

    # Формируем данные для круговой диаграммы
    return PieChartResponse(
        data=[
            CategoryStat(
                category=category,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total),
            )
            for category, amount in by_category.items()
        ]
    )


@router.get("/line")
async def get_line_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    timeframe: Literal["day", "week", "month", "year"] = "month",
) -> LineChartResponse:
    """📈 График расходов по временным отрезкам"""
    # Проверяем корректность временного интервала
    if timeframe not in TIME_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timeframe. Must be one of: {', '.join(TIME_FRAMES)}",
        )

    # Получаем все расходы пользователя
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()

    # Словарь для группировки по датам
    data: defaultdict[date, Decimal] = defaultdict(lambda: Decimal("0"))

    # Группируем расходы по выбранному временному интервалу
    for expense in expenses:
        day = expense.date.date()

        # Определяем ключ для группировки в зависимости от интервала
        if timeframe == "week":
            key = day - timedelta(days=day.weekday())
        elif timeframe == "year":
            key = date(
                year=day.year,
                month=day.month,
                day=1,
            )
        else:
            key = day

        data[key] += expense.amount

    # Формируем данные для линейного графика
    return LineChartResponse(
        timeframe=timeframe,
        data=[
            LinePoint(date=dt, amount=round_decimal(amount)) for dt, amount in sorted(data.items())
        ],
    )


@router.get("/compare")
async def compare_months(
    current_user: Annotated[User, Depends(get_current_user)],
) -> MonthComparison:
    """🔁 Сравнение текущего и прошлого месяца"""
    # Получаем текущую дату
    now = datetime.now(UTC)

    # Вычисляем начальные даты для текущего и прошлого месяца
    start_current = now.replace(day=1)
    start_previous = (start_current - timedelta(days=1)).replace(day=1)

    # Инициализируем счетчики
    current_total = previous_total = Decimal("0")

    # Получаем все расходы пользователя
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()

    # Считаем суммы за текущий и прошлый месяц
    for expense in expenses:
        if expense.date >= start_current:
            current_total += expense.amount
        elif start_previous <= expense.date < start_current:
            previous_total += expense.amount

    # Вычисляем процент изменения
    change_percent = (
        calculate_percent(current_total - previous_total, previous_total)
        if previous_total != Decimal("0")
        else Decimal("0")
    )

    # Формируем ответ
    return MonthComparison(
        previous_month_total=round_decimal(previous_total),
        current_month_total=round_decimal(current_total),
        change_percent=change_percent,
    )


@router.get("/budget-analysis")
async def get_budget_analysis(
    current_user: Annotated[User, Depends(get_current_user)],
) -> BudgetOverview:
    """
    🎯 Анализ использования бюджетов по категориям с учётом установленных лимитов
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Получаем все расходы пользователя
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()

    # Получаем все кастомные бюджеты пользователя
    budgets = await Budget.find(Budget.user_id == current_user.id).to_list()

    # Группируем траты по категориям
    spent_by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for expense in expenses:
        if expense.category:
            spent_by_category[expense.category] += expense.amount

    # Формируем список статистики по категориям
    categories = [
        BudgetCategoryStat(
            category=budget.category,
            budget=round_decimal(Decimal(str(budget.limit))),
            spent=round_decimal(spent_by_category.get(budget.category, Decimal("0"))),
            percent=calculate_percent(
                spent_by_category.get(budget.category, Decimal("0")),
                Decimal(str(budget.limit)),
            ),
        )
        for budget in budgets
    ]

    return BudgetOverview(categories=categories)
