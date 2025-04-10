from datetime import date
from decimal import Decimal
from typing import List, Literal

from pydantic import BaseModel

# ────────────── 📦 Типы ──────────────

# ────────────── 📦 Базовая сводка ──────────────


class TotalSpent(BaseModel):
    """
    💰 Общие траты по периодам.
    """

    week: Decimal
    month: Decimal
    year: Decimal


class CategoryStat(BaseModel):
    """
    📊 Траты по категориям.
    """

    category: str
    amount: Decimal
    percent: Decimal


class PaymentStat(BaseModel):
    """
    💳 Траты по способам оплаты.
    """

    method: str
    amount: Decimal
    percent: Decimal


class SummaryResponse(BaseModel):
    """
    📦 Ответ для /analytics/summary
    """

    total_spent: TotalSpent
    top_categories: List[CategoryStat]
    payment_methods: List[PaymentStat]


# ────────────── 🥧 Pie Chart (можно переиспользовать CategoryStat) ──────────────


class PieChartResponse(BaseModel):
    """
    🥧 Для pie chart по категориям
    """

    data: List[CategoryStat]


# ────────────── 📈 Line Chart ──────────────


class LinePoint(BaseModel):
    """
    📈 Точка на графике (дата → сумма)
    """

    date: date
    amount: Decimal


class LineChartResponse(BaseModel):
    """
    📈 Ответ для /analytics/line
    """

    timeframe: Literal["day", "week", "month", "year"]
    data: List[LinePoint]


# ────────────── 📊 Сравнение месяцев ──────────────


class MonthComparison(BaseModel):
    """
    🔁 Сравнение прошлого и текущего месяца
    """

    previous_month_total: Decimal
    current_month_total: Decimal
    change_percent: Decimal  # Положительное = рост, отрицательное = экономия


# ────────────── 🎯 Бюджет по категориям ──────────────


class BudgetCategoryStat(BaseModel):
    """
    🎯 Статистика по бюджету одной категории
    """

    category: str
    budget: Decimal
    spent: Decimal
    percent: Decimal


class BudgetOverview(BaseModel):
    """
    Все категории с бюджетом и расходами
    """

    categories: List[BudgetCategoryStat]


class IncomeExpenseComparison(BaseModel):
    """
    📊 Сравнение доходов и расходов за период
    """

    timeframe: Literal["week", "month", "year"]  # Период сравнения
    total_income: Decimal  # Общая сумма доходов
    total_expense: Decimal  # Общая сумма расходов
    difference: Decimal  # Разница (доходы - расходы)
    income_percent: Decimal  # Процент доходов от общей суммы
    expense_percent: Decimal  # Процент расходов от общей суммы
    top_income_categories: List[CategoryStat]  # Топ категории доходов
    top_expense_categories: List[CategoryStat]  # Топ категории расходов
