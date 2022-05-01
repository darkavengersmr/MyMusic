from pydantic import BaseModel, BaseSettings

class Playback(BaseModel):
    operation: str


