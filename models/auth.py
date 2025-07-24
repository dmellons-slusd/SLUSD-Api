from pydantic import BaseModel
from typing import Union

class Token(BaseModel):
    token: str
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

class UserCredentials(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    disabled: Union[bool, None] = None

class UserInDB(User):
    hashed_password: str

class BaseResponse(BaseModel):
    status: str
    message: str