from pydantic import BaseModel

class Users(BaseModel):
    username: str
    password: str