from pydantic import BaseModel, BaseSettings
from typing import List, Union


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
    mode: Union[str, None] = None
    genre: Union[str, None] = None
    artist: Union[str, None] = None
    year: Union[str, None] = None
    mood: Union[str, None] = None
    favorite: Union[str, None] = None
    now_play: Union[str, None] = None


class MyFilterQuery(BaseModel):
    type: str


class MyFilterOut(BaseModel):
    result: List[str] = []


class MyFilterSet(BaseModel):
    result: str


class PlayNowSet(BaseModel):
    result: str
