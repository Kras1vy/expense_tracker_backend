from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.models import PaymentMethod, User
from src.schemas.payment_method_schemas import (
    PaymentMethodCreate,
    PaymentMethodPublic,
    PaymentMethodUpdate,
)

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


@router.get("/")
async def get_user_payment_methods(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PaymentMethodPublic]:
    """
    🔍 Получить все платёжные методы пользователя
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    methods = await PaymentMethod.find(PaymentMethod.user_id == current_user.id).to_list()
    return [PaymentMethodPublic.model_validate(m.model_dump()) for m in methods]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    method_in: PaymentMethodCreate, current_user: Annotated[User, Depends(get_current_user)]
) -> PaymentMethodPublic:
    """
    ➕ Добавить платёжный метод
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    method = PaymentMethod(
        name=method_in.name,
        bank=method_in.bank,
        card_type=method_in.card_type,
        last4=method_in.last4,
        icon=method_in.icon,
        user_id=PydanticObjectId(current_user.id),
    )
    await method.insert()

    return PaymentMethodPublic.model_validate(method.model_dump())


@router.delete("/{method_id}")
async def delete_payment_method(
    method_id: PydanticObjectId, current_user: Annotated[User, Depends(get_current_user)]
) -> dict[str, str]:
    """
    ❌ Удалить платёжный метод
    """
    method = await PaymentMethod.get(method_id)
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    if method.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await method.delete()
    return {"detail": "Payment method deleted"}


@router.put("/{method_id}")
async def update_payment_method(
    method_id: str,
    method_in: PaymentMethodUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> PaymentMethodPublic:
    """
    ✏️ Обновление платёжного метода по ID
    """
    # Получаем метод по ID
    method = await PaymentMethod.get(PydanticObjectId(method_id))

    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")

    if method.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this method")

    # Обновляем поля
    if method_in.name is not None:
        method.name = method_in.name
    if method_in.bank is not None:
        method.bank = method_in.bank
    if method_in.card_type is not None:
        method.card_type = method_in.card_type
    if method_in.icon is not None:
        method.icon = method_in.icon

    await method.save()

    return PaymentMethodPublic.model_validate(method)


@router.get("/{method_id}")
async def get_payment_method_by_id(
    method_id: PydanticObjectId,
    current_user: Annotated[User, Depends(get_current_user)],
) -> PaymentMethodPublic:
    """
    🔍 Получить метод оплаты по ID (современный стиль Beanie + FastAPI)
    """
    method = await PaymentMethod.get(method_id)

    if not method or method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found"
        )

    return PaymentMethodPublic(**method.model_dump())
