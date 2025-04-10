from pydantic import BaseModel


class ExchangeTokenRequest(BaseModel):
    public_token: str
