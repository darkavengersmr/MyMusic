from pydantic import BaseModel, BaseSettings
from typing import List

class Settings(BaseSettings):
    USER: str
    PASSWORD: str
    SECRET_KEY: str
    EXCEPTION_PER_SEC_LIMIT: int
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"


class User(BaseModel):
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class Playback(BaseModel):
    operation: str
    username: str


class MyFilterQuery(BaseModel):
    type: str


class MyFilterOut(BaseModel):
    result: List[str] = []


class MyFilterSet(BaseModel):
    result: str
