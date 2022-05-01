from pydantic import BaseModel, BaseSettings


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
    username: str | None = None


class Playback(BaseModel):
    operation: str


