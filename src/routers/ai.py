import os
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from src.auth.dependencies import get_current_user
from src.models import Transaction, TransactionType, User
from src.utils.analytics_helper import round_decimal
from src.utils.error_messages import OPENAI_ERROR_MESSAGE, OPENAI_KEY_MISSING

# ────────────── 📍 Роутер AI ──────────────
router = APIRouter(prefix="/ai", tags=["AI"])

# ────────────── 🔐 Инициализация OpenAI ──────────────
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError(OPENAI_KEY_MISSING)

openai_client = AsyncOpenAI(api_key=openai_api_key)


# ────────────── 🤖 AI Endpoint для советов ──────────────
@router.get("/tips")
async def get_ai_tips(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str | list[str]]:
    """
    🤖 Возвращает советы по тратам, основанные на аналитике расходов пользователя.
    Использует GPT для генерации персонализированных рекомендаций.
    """
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Теперь получим расходы пользователя
    all_expenses = await Transaction.find(
        Transaction.user_id == current_user.id, Transaction.type == TransactionType.EXPENSE
    ).to_list()

    # Фильтруем расходы за текущий месяц
    expenses = []
    for exp in all_expenses:
        # Убедимся что дата расхода имеет часовой пояс UTC
        exp_date = exp.date.replace(tzinfo=UTC) if exp.date.tzinfo is None else exp.date
        if exp_date >= start_of_month:
            expenses.append(exp)

    if not expenses:
        raise HTTPException(status_code=404, detail="No expenses found to analyze")

    # 📊 Группируем по категориям
    by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total: Decimal = Decimal("0")

    for exp in expenses:
        amount: Decimal = exp.amount
        if exp.category:
            by_category[exp.category] += amount
            total += amount

    assert isinstance(total, Decimal)  # Ensure total is Decimal

    # ✍️ Составляем текст для GPT
    analysis_text = "\n".join(
        [f"- {cat}: {round_decimal(amount)} CAD" for cat, amount in by_category.items()]
    )

    system_prompt = (
        "Ты дерзкий и умный финансовый коуч. Пиши строго по делу, кратко. "
        "Советы — полезные, конкретные. Без воды и повторов."
    )

    user_prompt = (
        f"Расходы за месяц: {round_decimal(total)} CAD.\n"
        f"Категории:\n{analysis_text}\n\n"
        f"Дай 3 совета, как улучшить мои траты."
    )

    # 🚀 Отправляем запрос в OpenAI
    try:
        response = await openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=OPENAI_ERROR_MESSAGE.format(str(e))) from e

    # 📤 Возвращаем список советов
    answer = response.choices[0].message.content
    model_used = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    return {"model": model_used, "tips": answer.strip().split("\n") if answer else ["Нет совета"]}
