from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

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
    top_categories: list[CategoryStat]
    payment_methods: list[PaymentStat]


# ────────────── 🥧 Pie Chart (можно переиспользовать CategoryStat) ──────────────


class PieChartResponse(BaseModel):
    """
    🥧 Для pie chart по категориям
    """

    data: list[CategoryStat]


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
    data: list[LinePoint]


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
    remaining: Decimal
    percent_used: Decimal


class BudgetOverview(BaseModel):
    """
    Все категории с бюджетом и расходами
    """

    categories: list[BudgetCategoryStat]
