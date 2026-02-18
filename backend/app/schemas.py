from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Users(BaseModel):
    username: str
    password: str

class PhotoUploadResponse(BaseModel):
    message: str
    output: str