from functools import lru_cache
from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    OPENAI_API_KEY: str
    GOOGLE_CSE_ID: str
    GOOGLE_API_KEY: str
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
