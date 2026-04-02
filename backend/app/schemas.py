from pydantic import BaseModel

class Users(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    username: str


class RefreshRequest(BaseModel):
    refresh_token: str