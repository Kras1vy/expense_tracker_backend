from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException
from plaid.api_client import ApiException
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.item_public_token_exchange_response import ItemPublicTokenExchangeResponse
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from src.auth.dependencies import get_current_user
from src.integrations.plaid import plaid_client
from src.models import BankAccount, BankConnection, BankTransaction, User
from src.schemas.plaid import ExchangeTokenRequest

router = APIRouter(prefix="/plaid", tags=["Plaid"])


@router.post("/link-token")
async def create_link_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    try:
        request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=str(current_user.id)),
            client_name="Expense Tracker",
            products=[Products("transactions")],
            country_codes=[CountryCode("US"), CountryCode("CA")],
            language="en",
        )
        response = plaid_client.link_token_create(request)
        return {"link_token": response["link_token"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid error: {e!s}") from e


# src/routers/plaid.py


@router.post("/exchange-public-token")
async def exchange_public_token(
    data: ExchangeTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Получить access_token и item_id из public_token, полученного от фронта после подключения банка.
    """
    request = ItemPublicTokenExchangeRequest(public_token=data.public_token)

    try:
        response = cast(
            "ItemPublicTokenExchangeResponse", plaid_client.item_public_token_exchange(request)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    access_token = response.access_token
    item_id = response.item_id

    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is required")

    assert current_user.id is not None  # type assertion for type checker
    bank_connection = BankConnection(
        user_id=current_user.id,
        access_token=access_token,
        item_id=item_id,
    )
    await bank_connection.insert()

    return {
        "status": "success",
        "message": "Bank account connected",
        "item_id": item_id,  # item_id безопасен, его можно возвращать
    }


@router.get("/accounts")
async def get_and_save_bank_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    # Получаем все access_token'ы пользователя
    connections = await BankConnection.find(BankConnection.user_id == current_user.id).to_list()

    if not connections:
        raise HTTPException(status_code=404, detail="No bank connections found")

    saved_accounts = []

    for conn in connections:
        try:
            request = AccountsGetRequest(access_token=conn.access_token)
            response = plaid_client.accounts_get(request)
            for acc in response.accounts:
                # Проверим: уже сохранён этот аккаунт?
                existing = await BankAccount.find_one(
                    BankAccount.account_id == cast("str", acc.account_id)
                )
                if existing:
                    continue

                assert current_user.id is not None  # type assertion for type checker
                assert conn.id is not None  # type assertion for type checker
                account = BankAccount(
                    user_id=current_user.id,
                    bank_connection_id=conn.id,
                    account_id=cast("str", acc.account_id),
                    name=cast("str", acc.name),
                    official_name=cast("str | None", acc.official_name),
                    type=cast("str", acc.type.value),
                    subtype=cast("str | None", acc.subtype.value if acc.subtype else None),
                    mask=cast("str | None", acc.mask),
                    current_balance=cast("float | None", acc.balances.current),
                    available_balance=cast("float | None", acc.balances.available),
                    iso_currency_code=cast("str | None", acc.balances.iso_currency_code),
                )
                await account.insert()
                saved_accounts.append(account.model_dump())
        except ApiException as e:
            print(f"❌ Plaid API error: {e}")
            continue
        except ValueError as e:
            print(f"❌ Invalid data from Plaid: {e}")
            continue

    return saved_accounts


@router.get("/transactions")
async def sync_and_get_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    # Получаем все bank accounts пользователя
    accounts = await BankAccount.find(BankAccount.user_id == current_user.id).to_list()
    if not accounts:
        raise HTTPException(status_code=404, detail="No bank accounts found")

    transactions_to_return: list[dict[str, Any]] = []

    for account in accounts:
        connection = await BankConnection.get(account.bank_connection_id)
        if not connection:
            continue

        assert current_user.id is not None
        assert account.id is not None
        assert connection.access_token is not None

        try:
            start_date = (datetime.now(UTC) - timedelta(days=30)).date()
            end_date = datetime.now(UTC).date()

            request = TransactionsGetRequest(
                access_token=connection.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(account_ids=[account.account_id]),
            )

            response = plaid_client.transactions_get(request)

            for txn in response.transactions:
                exists = await BankTransaction.find_one(
                    BankTransaction.transaction_id == cast("str", txn.transaction_id)
                )
                if exists:
                    continue

                transaction = BankTransaction(
                    user_id=current_user.id,
                    bank_account_id=account.id,
                    transaction_id=cast("str", txn.transaction_id),
                    name=cast("str", txn.name),
                    amount=cast("float", txn.amount),
                    date=cast("date", txn.date),
                    category=cast("list[str] | None", txn.category),
                    payment_channel=cast("str | None", txn.payment_channel),
                    iso_currency_code=cast("str | None", txn.iso_currency_code),
                    pending=cast("bool", txn.pending),
                )
                await transaction.insert()
                transactions_to_return.append(transaction.model_dump())

        except ApiException as e:
            print(f"❌ Plaid API error: {e}")
            continue
        except ValueError as e:
            print(f"❌ Invalid data from Plaid: {e}")
            continue

    return sorted(transactions_to_return, key=lambda x: x["date"], reverse=True)
