from plaid.api.plaid_api import PlaidApi
from plaid.api_client import ApiClient
from plaid.configuration import Configuration

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
