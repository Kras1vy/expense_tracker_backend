from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ────────────── 📦 Типы ──────────────

# ────────────── 📦 Базовая сводка ──────────────


class DecimalModel(BaseModel):
    """Base model with Decimal to float conversion"""

    model_config = ConfigDict(json_encoders={Decimal: float})


class TotalAmount(DecimalModel):
    """
    💰 Общие суммы по периодам.
    """

    week: Decimal
    month: Decimal
    year: Decimal


class CategoryStat(DecimalModel):
    """
    📊 Траты по категориям.
    """

    category: str
    amount: Decimal
    percent: Decimal


class PaymentStat(DecimalModel):
    """
    💳 Траты по способам оплаты.
    """

    method: str
    amount: Decimal
    percent: Decimal


class PeriodStat(DecimalModel):
    """
    📅 Статистика за период
    """

    total_spent: Decimal
    total_earned: Decimal
    net_amount: Decimal


class SummaryResponse(DecimalModel):
    """
    📦 Ответ для /analytics/summary
    """

    total_spent: TotalAmount
    total_earned: TotalAmount
    net_amount: TotalAmount  # Разница между доходами и расходами
    by_period: dict[str, PeriodStat]  # Статистика по периодам (week, month, year)
    top_categories: list[CategoryStat]
    payment_methods: list[PaymentStat]


# ────────────── 🥧 Pie Chart (можно переиспользовать CategoryStat) ──────────────


class PieChartResponse(DecimalModel):
    """
    🥧 Для pie chart по категориям
    """

    data: list[CategoryStat]


# ────────────── 📈 Line Chart ──────────────


class LinePoint(DecimalModel):
    """
    📈 Точка на графике (дата → сумма)
    """

    date: date
    amount: Decimal


class LineChartResponse(DecimalModel):
    """
    📈 Ответ для /analytics/line
    """

    timeframe: Literal["day", "week", "month", "year"]
    data: list[LinePoint]


# ────────────── 📊 Сравнение месяцев ──────────────


class MonthComparison(DecimalModel):
    """
    🔁 Сравнение прошлого и текущего месяца
    """

    previous_month_total: Decimal
    current_month_total: Decimal
    change_percent: Decimal  # Положительное = рост, отрицательное = экономия


# ────────────── 🎯 Бюджет по категориям ──────────────


class BudgetCategoryStat(DecimalModel):
    """
    🎯 Статистика по бюджету одной категории
    """

    category: str
    budget: Decimal
    spent: Decimal
    percent: Decimal


class BudgetOverview(DecimalModel):
    """
    Все категории с бюджетом и расходами
    """

    total_budget: Decimal
    total_spent: Decimal
    remaining: Decimal
    categories: list[BudgetCategoryStat]


class IncomeExpenseComparison(DecimalModel):
    """
    📊 Сравнение доходов и расходов за период
    """

    timeframe: Literal["week", "month", "year"]  # Период сравнения
    total_income: Decimal  # Общая сумма доходов
    total_expense: Decimal  # Общая сумма расходов
    difference: Decimal  # Разница (доходы - расходы)
    income_percent: Decimal  # Процент доходов от общей суммы
    expense_percent: Decimal  # Процент расходов от общей суммы
    top_income_categories: list[CategoryStat]  # Топ категории доходов
    top_expense_categories: list[CategoryStat]  # Топ категории расходов
