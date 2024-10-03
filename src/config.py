import os
from dataclasses import dataclass
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str
    DB_SCHEMA: str = "soundscan"
    DEV_MODE: bool = False
    OPERATING_PORT: Optional[int] = None
    SERIAL_BAUD_RATE: Optional[int] = None

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@dataclass
class DB_Configuration:
    DB_URL = os.getenv("DB_NAME", "")

settings = Settings()

DB_DATA = DB_Configuration()
