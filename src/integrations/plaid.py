from plaid.api.plaid_api import PlaidApi
from plaid.api_client import ApiClient
from plaid.configuration import Configuration
from plaid.model.country_code import CountryCode
from plaid.model.depository_filter import DepositoryFilter
from plaid.model.link_token_account_filters import LinkTokenAccountFilters
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products

from src.config import config

# Настройка конфигурации
configuration = Configuration(
    host="https://sandbox.plaid.com"
    if config.PLAID_ENV == "sandbox"
    else "https://development.plaid.com",
    api_key={
        "clientId": config.PLAID_CLIENT_ID,
        "secret": config.PLAID_SECRET,
    },
)

api_client: ApiClient = ApiClient(configuration)
plaid_client: PlaidApi = PlaidApi(api_client)
