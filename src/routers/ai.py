import os
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from src.auth.dependencies import get_current_user
from src.models import Expense, User
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
) -> dict[str, list[str]]:
    """
    🤖 Возвращает советы по тратам, основанные на аналитике расходов пользователя.
    Использует GPT для генерации персонализированных рекомендаций.
    """
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)
    print(f"Start of month: {start_of_month} ({type(start_of_month)})")

    # 📦 Загружаем расходы за текущий месяц
    print(f"Current user ID: {current_user.id} (type: {type(current_user.id)})")

    # Сначала получим все расходы для отладки
    all_db_expenses = await Expense.find_all().to_list()
    print(f"Total expenses in DB: {len(all_db_expenses)}")
    for exp in all_db_expenses:
        print(
            f"Expense: user_id={exp.user_id} (type: {type(exp.user_id)}), amount={exp.amount}, category={exp.category}"
        )

    # Теперь получим расходы пользователя
    all_expenses = await Expense.find({"user_id": current_user.id}).to_list()
    print(f"Found expenses: {len(all_expenses)}")

    # Получаем начало текущего месяца в UTC
    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)
    print(f"Start of month: {start_of_month} ({type(start_of_month)})")

    # Фильтруем расходы за текущий месяц
    expenses = []
    for exp in all_expenses:
        # Убедимся что дата расхода имеет часовой пояс UTC
        exp_date = exp.date.replace(tzinfo=UTC) if exp.date.tzinfo is None else exp.date
        print(f"Expense date: {exp_date} ({type(exp_date)}), amount: {exp.amount}")
        print(f"Date comparison: {exp_date} >= {start_of_month} = {exp_date >= start_of_month}")

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

    # ✍️ Составляем текст для GPT
    analysis_text = "\n".join(
        [f"- {cat}: {round_decimal(amount)} CAD" for cat, amount in by_category.items()]
    )

    prompt = (
        f"У меня есть расходы за месяц на сумму {round_decimal(total)} CAD.\n"  # type: ignore
        f"Вот разбивка по категориям:\n"
        f"{analysis_text}\n\n"
        f"Проанализируй мои расходы и предложи 3 коротких совета, как улучшить моё финансовое поведение. Учитывай, какие категории самые большие."
    )

    # 🚀 Отправляем запрос в OpenAI
    try:
        response = await openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {
                    "role": "system",
                    "content": "Ты финансовый помощник, эксперт по личным финансам.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "300")),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=OPENAI_ERROR_MESSAGE.format(str(e))) from e

    # 📤 Возвращаем список советов
    answer = response.choices[0].message.content
    return {"tips": answer.strip().split("\n") if answer else ["Нет совета"]}
