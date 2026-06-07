import os
import sys
import logging
from pydantic_settings import BaseSettings
from typing import List, Optional

logger = logging.getLogger("uvicorn.error")


class Settings(BaseSettings):
    # ── Auth / JWT ────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cambia-esto-en-produccion")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15          # reducido a 15 min (seguridad)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Orígenes permitidos separados por coma. "*" solo en development.
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost,http://localhost:3000,http://10.0.2.2"
    )

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LOGIN_PER_MINUTE: int = 5          # intentos de login por IP/minuto
    RATE_REGISTER_PER_MINUTE: int = 3       # registros por IP/minuto
    RATE_GENERAL_PER_MINUTE: int = 60       # requests generales por IP/minuto

    # ── Lockout de login fallido ──────────────────────────────────────────────
    LOGIN_LOCKOUT_MAX_ATTEMPTS: int = 10    # intentos antes del bloqueo
    LOGIN_LOCKOUT_DURATION_SEC: int = 900   # 15 minutos de bloqueo

    # ── SMTP ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_FROM: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # ── URL pública ───────────────────────────────────────────────────────────
    PUBLIC_URL: str = "https://one-piece-tcg-server-production.up.railway.app"

    # ── Entorno ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ── Eliminación de cuenta ─────────────────────────────────────────────────
    # Período de gracia (días) entre la solicitud de eliminación y la purga
    # definitiva de los datos. Durante este período el usuario puede recuperar
    # la cuenta iniciando sesión.
    ACCOUNT_DELETION_GRACE_DAYS: int = int(os.getenv("ACCOUNT_DELETION_GRACE_DAYS", "30"))

    # ── Feature flags ─────────────────────────────────────────────────────────
    # Modelo freemium. Por defecto True (comportamiento actual: límites Free y
    # escaneo masivo solo Premium). En el despliegue de la versión gratuita
    # (Play Store) se setea FREEMIUM_ENABLED=false para liberar funciones
    # Premium-only (p.ej. escaneo masivo) a todos los usuarios.
    FREEMIUM_ENABLED: bool = os.getenv("FREEMIUM_ENABLED", "true").lower() == "true"

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> List[str]:
        """Devuelve CORS_ORIGINS como lista."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def validate_security(self):
        """Valida configuración crítica al arrancar. Detiene el proceso si hay problemas graves."""
        warnings = []
        if self.SECRET_KEY == "cambia-esto-en-produccion":
            msg = (
                "SECURITY ERROR: SECRET_KEY usa el valor por defecto. "
                "Define la variable de entorno SECRET_KEY con un valor secreto y único."
            )
            if self.ENVIRONMENT == "production":
                logger.critical(msg)
                sys.exit(1)           # aborta en producción
            else:
                warnings.append(msg)  # solo alerta en desarrollo

        for w in warnings:
            logger.warning(w)


settings = Settings()
