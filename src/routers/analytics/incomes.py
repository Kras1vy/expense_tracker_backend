from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.config import TIME_FRAMES
from src.models import Expense, Income, User
from src.schemas.analytics_schemas import (
    CategoryStat,
    IncomeExpenseComparison,
    IncomeLineChartResponse,
    IncomeSummary,
    LinePoint,
    MonthComparison,
    TotalSpent,
)
from src.utils.analytics_helper import calculate_percent, round_decimal

router = APIRouter(prefix="/incomes", tags=["Income Analytics"])


@router.get("/summary")
async def get_summary(current_user: Annotated[User, Depends(get_current_user)]) -> IncomeSummary:
    """
    📊 Общая аналитика доходов:
    - Суммы за неделю / месяц / год
    - Топ 5 категорий
    - Распределение по источникам
    """
    # Получаем текущую дату и время
    now = datetime.now(UTC)

    # Вычисляем начальные даты для разных периодов
    start_of_week = now - timedelta(days=now.weekday())
    start_of_month = now.replace(day=1)
    start_of_year = now.replace(month=1, day=1)

    # Получаем все доходы пользователя
    incomes = await Income.find(Income.user_id == current_user.id).to_list()

    # Инициализируем счетчики для разных периодов
    total_week: Decimal = Decimal("0")
    total_month: Decimal = Decimal("0")
    total_year: Decimal = Decimal("0")
    total_all: Decimal = Decimal("0")

    # Словари для группировки по категориям и источникам
    by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_source: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    # Считаем суммы по периодам и категориям
    for income in incomes:
        # Общая сумма
        total_all += income.amount

        # Суммы по периодам
        if income.date >= start_of_year:
            total_year += income.amount
        if income.date >= start_of_month:
            total_month += income.amount
        if income.date >= start_of_week:
            total_week += income.amount

        # Группируем по категориям и источникам
        if income.category:
            by_category[income.category] += income.amount
        if income.source:
            by_source[income.source] += income.amount

    # Получаем топ-5 категорий по доходам
    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]

    # Формируем ответ
    return IncomeSummary(
        total_income=TotalSpent(
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
        income_sources=[
            CategoryStat(
                category=source,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total_all),
            )
            for source, amount in by_source.items()
        ],
    )


@router.get("/line")
async def get_line_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    timeframe: Literal["day", "week", "month", "year"] = "month",
) -> IncomeLineChartResponse:
    """📈 График доходов по временным отрезкам"""
    # Проверяем корректность временного интервала
    if timeframe not in TIME_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timeframe. Must be one of: {', '.join(TIME_FRAMES)}",
        )

    # Получаем все доходы пользователя
    incomes = await Income.find(Income.user_id == current_user.id).to_list()

    # Словарь для группировки по датам
    data: defaultdict[date, Decimal] = defaultdict(lambda: Decimal("0"))

    # Группируем доходы по выбранному временному интервалу
    for income in incomes:
        day = income.date.date()

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

        data[key] += income.amount

    # Формируем данные для линейного графика
    return IncomeLineChartResponse(
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

    # Получаем все доходы пользователя
    incomes = await Income.find(Income.user_id == current_user.id).to_list()

    # Считаем суммы за текущий и прошлый месяц
    for income in incomes:
        if income.date >= start_current:
            current_total += income.amount
        elif start_previous <= income.date < start_current:
            previous_total += income.amount

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


@router.get("/compare-with-expenses")
async def compare_with_expenses(
    current_user: Annotated[User, Depends(get_current_user)],
    timeframe: Literal["week", "month", "year"] = "month",
) -> IncomeExpenseComparison:
    """
    📊 Сравнение доходов и расходов:
    - Общие суммы за период
    - Разница между доходами и расходами
    - Процентное соотношение
    - Топ категории по обоим типам
    """
    # Получаем текущую дату
    now = datetime.now(UTC)

    # Вычисляем начальную дату для периода
    if timeframe == "week":
        start_date = now - timedelta(days=now.weekday())
    elif timeframe == "month":
        start_date = now.replace(day=1)
    else:  # year
        start_date = now.replace(month=1, day=1)

    # Получаем доходы и расходы за период
    incomes = await Income.find(
        Income.user_id == current_user.id, Income.date >= start_date
    ).to_list()

    expenses = await Expense.find(
        Expense.user_id == current_user.id, Expense.date >= start_date
    ).to_list()

    # Считаем общие суммы
    total_income = sum(Decimal(str(income.amount)) for income in incomes) or Decimal("0")
    total_expense = sum(Decimal(str(expense.amount)) for expense in expenses) or Decimal("0")

    # Считаем разницу
    difference = total_income - total_expense

    # Группируем по категориям
    income_by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    expense_by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for income in incomes:
        if income.category:
            income_by_category[income.category] += income.amount

    for expense in expenses:
        if expense.category:
            expense_by_category[expense.category] += expense.amount

    # Получаем топ категории
    top_income_categories = sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]
    top_expense_categories = sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]

    # Формируем ответ
    return IncomeExpenseComparison(
        timeframe=timeframe,
        total_income=round_decimal(total_income),
        total_expense=round_decimal(total_expense),
        difference=round_decimal(difference),
        income_percent=calculate_percent(total_income, total_income + total_expense)
        if total_income + total_expense > 0
        else Decimal("0"),
        expense_percent=calculate_percent(total_expense, total_income + total_expense)
        if total_income + total_expense > 0
        else Decimal("0"),
        top_income_categories=[
            CategoryStat(
                category=category,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total_income)
                if total_income > 0
                else Decimal("0"),
            )
            for category, amount in top_income_categories
        ],
        top_expense_categories=[
            CategoryStat(
                category=category,
                amount=round_decimal(amount),
                percent=calculate_percent(amount, total_expense)
                if total_expense > 0
                else Decimal("0"),
            )
            for category, amount in top_expense_categories
        ],
    )
