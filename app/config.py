import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cambia-esto-en-produccion")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # SMTP — configura estas variables en Railway para habilitar emails
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_FROM: Optional[str] = None      # tu_correo@gmail.com
    SMTP_PASSWORD: Optional[str] = None  # App Password de Gmail

    # URL base pública del servidor (para links en emails)
    PUBLIC_URL: str = "https://one-piece-tcg-server-production.up.railway.app"

    class Config:
        env_file = ".env"

settings = Settings()