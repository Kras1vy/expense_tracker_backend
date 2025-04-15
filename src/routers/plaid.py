# Import regular expression module for pattern matching
import re

# Import time-related modules for date and time operations
from datetime import UTC, date, datetime, timedelta

# Import type checking related modules
from typing import TYPE_CHECKING, Annotated, Any, cast

# Import Beanie ODM for MongoDB operations
from beanie import PydanticObjectId

# Import FastAPI related modules for routing and request handling
from fastapi import APIRouter, Depends, Path, Query

# Import Plaid API related modules
from plaid.api_client import ApiException
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

# Import authentication dependencies
from src.auth.dependencies import get_current_user
from src.auth.exceptions import (
    raise_forbidden_error,
    raise_invalid_data_error,
    raise_missing_field_error,
    raise_not_found_error,
    raise_plaid_api_error,
)

# Import Plaid client configuration
from src.integrations.plaid import plaid_client

# Import database models
from src.models import BankAccount, BankConnection, BankTransaction, Category, User

# Import Plaid related schemas
from src.schemas.plaid import ExchangeTokenRequest

# Import utility function for balance recalculation
from src.utils.recalculate_user_balance import recalculate_user_balance

# Type checking imports for better type hints
if TYPE_CHECKING:
    from plaid.model.item_public_token_exchange_response import ItemPublicTokenExchangeResponse

# Create a router instance for Plaid-related endpoints
router = APIRouter(prefix="/plaid", tags=["Plaid"])


@router.post("/link-token")
async def create_link_token(
    # Get the current authenticated user
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    try:
        # Create a request to generate a Plaid link token
        request = LinkTokenCreateRequest(
            # Set the user ID for the link token
            user=LinkTokenCreateRequestUser(client_user_id=str(current_user.id)),
            # Set the application name
            client_name="Expense Tracker",
            # Specify required Plaid products
            products=[Products("transactions")],
            # Set supported country codes
            country_codes=[CountryCode("US"), CountryCode("CA")],
            # Set the language
            language="en",
        )
        # Make API call to Plaid to create link token
        response = plaid_client.link_token_create(request)
        # Return the generated link token
        return {"link_token": response["link_token"]}
    except ApiException as e:
        # Handle Plaid API errors
        raise_plaid_api_error(e)
    except (ValueError, KeyError) as e:
        # Handle invalid data errors
        raise_invalid_data_error(e)


@router.post("/exchange-public-token")
async def exchange_public_token(
    # Get the request data containing public token
    data: ExchangeTokenRequest,
    # Get the current authenticated user
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Exchange public token for access token and item ID after bank connection
    """
    # Create request to exchange public token
    request = ItemPublicTokenExchangeRequest(public_token=data.public_token)

    try:
        # Make API call to Plaid to exchange the token
        response = cast(
            "ItemPublicTokenExchangeResponse", plaid_client.item_public_token_exchange(request)
        )
    except ApiException as e:
        # Handle Plaid API errors
        raise_plaid_api_error(e)
    except (ValueError, KeyError) as e:
        # Handle invalid data errors
        raise_invalid_data_error(e)

    # Extract access token and item ID from response
    access_token = response.access_token
    item_id = response.item_id

    # Try to get institution ID and name
    institution_id = getattr(response, "institution_id", None)
    institution_name: str | None = None

    if institution_id:
        try:
            # Make API call to get institution details
            inst_response = plaid_client.institutions_get_by_id(
                InstitutionsGetByIdRequest(
                    institution_id=institution_id,
                    country_codes=[CountryCode("US"), CountryCode("CA")],
                )
            )
            # Extract institution name from response
            institution_name = inst_response.institution.name
        except ApiException as e:
            # Log Plaid API errors
            print(f"⚠️ Plaid API error: {e}")
        except (ValueError, KeyError) as e:
            # Log invalid data errors
            print(f"⚠️ Invalid data: {e}")

    # Verify user ID exists
    if not current_user.id:
        raise_missing_field_error("User ID")

    # Create new bank connection record
    bank_connection = BankConnection(
        user_id=current_user.id,
        access_token=access_token,
        item_id=item_id,
        institution_id=institution_id,
        institution_name=cast("str | None", institution_name),
    )
    # Save bank connection to database
    _ = await bank_connection.insert()

    # Return success response
    return {
        "status": "success",
        "message": "Bank account connected",
        "item_id": item_id,
        "institution_name": institution_name,
    }


@router.get("/accounts")
async def get_and_save_bank_accounts(
    # Get the current authenticated user
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    # Get all bank connections for the user
    connections = await BankConnection.find(BankConnection.user_id == current_user.id).to_list()

    # Check if any connections exist
    if not connections:
        raise_not_found_error("No bank connections found")

    # List to store newly saved accounts
    saved_accounts = []

    # Process each bank connection
    for conn in connections:
        try:
            # Create request to get accounts
            request = AccountsGetRequest(access_token=conn.access_token)
            # Make API call to Plaid
            response = plaid_client.accounts_get(request)
            # Process each account
            for acc in response.accounts:
                # Check if account already exists
                existing = await BankAccount.find_one(
                    BankAccount.account_id == cast("str", acc.account_id)
                )
                if existing:
                    continue

                # Verify required IDs exist
                if not current_user.id:
                    raise_missing_field_error("User ID")
                if not conn.id:
                    raise_missing_field_error("Connection ID")

                # Create new bank account record
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
                # Save account to database
                _ = await account.insert()
                # Add account to saved accounts list
                saved_accounts.append(account.model_dump())
        except ApiException as e:
            # Log Plaid API errors
            print(f"❌ Plaid API error: {e}")
            continue
        except ValueError as e:
            # Log invalid data errors
            print(f"❌ Invalid data from Plaid: {e}")
            continue

    # Return list of saved accounts
    return saved_accounts


@router.get("/transactions")
async def sync_and_get_transactions(
    # Get the current authenticated user
    current_user: Annotated[User, Depends(get_current_user)],
    # Optional account type filter
    account_type: Annotated[str | None, Query] = None,
) -> list[dict[str, Any]]:
    # Build query for bank accounts
    account_query = BankAccount.find(BankAccount.user_id == current_user.id)
    if account_type:
        account_query = account_query.find(BankAccount.type == account_type)

    # Get accounts matching the query
    accounts = await account_query.to_list()
    if not accounts:
        raise_not_found_error("No bank accounts found")

    # List to store transactions to return
    transactions_to_return: list[dict[str, Any]] = []

    # Process each account
    for account in accounts:
        # Get associated bank connection
        connection = await BankConnection.get(account.bank_connection_id)
        if not connection or not connection.access_token:
            raise_missing_field_error(
                "Invalid bank connection or missing access token. Please reconnect."
            )

        try:
            # Set date range for transaction sync
            start_date = (datetime.now(UTC) - timedelta(days=30)).date()
            end_date = datetime.now(UTC).date()

            # Create request to get transactions
            request = TransactionsGetRequest(
                access_token=connection.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(account_ids=[account.account_id]),
            )

            # Make API call to Plaid
            response = plaid_client.transactions_get(request)

            # Process each transaction
            for txn in response.transactions:
                # Check if transaction already exists
                exists = await BankTransaction.find_one(
                    BankTransaction.transaction_id == cast("str", txn.transaction_id)
                )
                if exists:
                    continue

                # Get Plaid category
                plaid_category = txn.category[0] if txn.category else "Uncategorized"
                plaid_category_str = cast("str", plaid_category)

                # Find or create category
                category = await Category.find_one(
                    {
                        "user_id": current_user.id,
                        "name": {"$regex": f"^{re.escape(plaid_category_str)}$", "$options": "i"},
                    }
                )

                if not category:
                    # Create new category if it doesn't exist
                    category = Category(
                        name=cast("str", plaid_category).strip(),
                        user_id=current_user.id,
                        icon="📦",
                        color="#9CA3AF",
                        is_default=False,
                    )
                    _ = await category.insert()

                # Map payment channels to payment methods
                channel_map = {
                    "online": "Plaid - Online",
                    "in store": "Plaid - Card",
                    "other": "Plaid - Other",
                }
                payment_method = channel_map.get(
                    cast("str", txn.payment_channel), "Plaid - Unknown"
                )

                # Create new transaction record
                transaction = BankTransaction(
                    user_id=cast("PydanticObjectId", current_user.id),
                    bank_account_id=cast("PydanticObjectId", account.id),
                    transaction_id=cast("str", txn.transaction_id),
                    name=cast("str", txn.name),
                    amount=cast("float", txn.amount),
                    date=cast("date", txn.date),
                    category=[category.name],
                    payment_channel=cast("str | None", txn.payment_channel),
                    payment_method=payment_method,
                    iso_currency_code=cast("str | None", txn.iso_currency_code),
                    pending=cast("bool", txn.pending),
                    source="plaid",
                )
                # Save transaction to database
                _ = await transaction.insert()
                # Add transaction to return list
                transactions_to_return.append(transaction.model_dump())

        except ApiException as e:
            # Log Plaid API errors
            print(f"❌ Plaid API error: {e}")
            continue
        except ValueError as e:
            # Log invalid data errors
            print(f"❌ Invalid data from Plaid: {e}")
            continue

    # Recalculate user balance if user ID exists
    if current_user.id:
        await recalculate_user_balance(current_user.id)

    # Return sorted transactions
    return sorted(transactions_to_return, key=lambda x: x["date"], reverse=True)


@router.delete("/connection/{connection_id}")
async def delete_bank_connection(
    # Get the current authenticated user
    current_user: Annotated[User, Depends(get_current_user)],
    # Get connection ID from path
    connection_id: Annotated[PydanticObjectId, Path(description="ID банковской связки")],
) -> dict[str, str]:
    """
    Delete bank connection and all related accounts and transactions
    """
    # Get bank connection
    connection = await BankConnection.get(connection_id)
    if not connection:
        raise_not_found_error("Bank connection not found")

    # Verify user owns the connection
    if connection.user_id != current_user.id:
        raise_forbidden_error("Not authorized to access this bank connection")

    # Get all associated bank accounts
    accounts = await BankAccount.find(BankAccount.bank_connection_id == connection.id).to_list()
    # Delete all transactions and accounts
    for acc in accounts:
        _ = await BankTransaction.find(BankTransaction.bank_account_id == acc.id).delete()
        _ = await acc.delete()

    # Delete the connection
    _ = await connection.delete()

    # Recalculate user balance
    if current_user.id:
        await recalculate_user_balance(current_user.id)

    # Return success message
    return {"message": "Bank connection and related data deleted"}


@router.get("/transactions/sync-latest")
async def sync_latest_transactions(
    # Get the current authenticated user
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Sync latest transactions from Plaid (without duplicates)
    """
    # Get all user's bank accounts
    accounts = await BankAccount.find(BankAccount.user_id == current_user.id).to_list()
    if not accounts:
        raise_not_found_error("No bank accounts found")

    # Counter for imported transactions
    imported = 0

    # Process each account
    for account in accounts:
        # Get associated bank connection
        connection = await BankConnection.get(account.bank_connection_id)
        if not connection:
            continue

        try:
            # Set date range for transaction sync (last 3 days)
            start_date = (datetime.now(UTC) - timedelta(days=3)).date()
            end_date = datetime.now(UTC).date()

            # Create request to get transactions
            request = TransactionsGetRequest(
                access_token=connection.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(account_ids=[account.account_id]),
            )

            # Make API call to Plaid
            response = plaid_client.transactions_get(request)

            # Process each transaction
            for txn in response.transactions:
                # Check if transaction already exists
                exists = await BankTransaction.find_one(
                    BankTransaction.transaction_id == cast("str", txn.transaction_id)
                )
                if exists:
                    continue

                # Verify required IDs exist
                if not current_user.id:
                    raise_missing_field_error("User ID")
                if not account.id:
                    raise_missing_field_error("Account ID")

                # Create new transaction record
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
                # Save transaction to database
                _ = await transaction.insert()
                # Increment imported counter
                imported += 1

        except ApiException as e:
            # Log Plaid API errors
            print(f"❌ Plaid API error: {e}")
            continue

    # Recalculate user balance
    if current_user.id:
        await recalculate_user_balance(current_user.id)

    # Return success response with import count
    return {"status": "success", "imported": imported}
