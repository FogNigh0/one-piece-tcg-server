# app/core/rate_limiter.py
# Rate limiter (slowapi) + bloqueo por intentos fallidos de login.
#
# El tracker de intentos fallidos usa memoria del proceso.
# Para deployments multi-proceso, migrar a Redis.

import time
import threading
import logging
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import settings

logger = logging.getLogger("uvicorn.error")

# ── slowapi limiter (instancia global) ────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def get_client_ip(request: Request) -> str:
    """Extrae IP real respetando X-Forwarded-For del proxy de Railway."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Tracker de intentos fallidos ──────────────────────────────────────────────

_lock = threading.Lock()

# { "ip:identifier": {"count": int, "first": float, "locked_until": float} }
_failed_attempts: dict[str, dict] = {}

_MAX = settings.LOGIN_LOCKOUT_MAX_ATTEMPTS
_DUR = settings.LOGIN_LOCKOUT_DURATION_SEC


def is_login_locked(ip: str, identifier: str) -> float | None:
    """Devuelve segundos restantes de bloqueo, o None si el login está permitido."""
    key = f"{ip}:{identifier.lower()}"
    now = time.monotonic()
    with _lock:
        rec = _failed_attempts.get(key)
        if rec is None:
            return None
        locked_until = rec.get("locked_until", 0.0)
        if now >= locked_until:
            # Ventana expirada → limpia
            del _failed_attempts[key]
            return None
        return locked_until - now


def record_failed_login(ip: str, identifier: str) -> int:
    """Registra un intento fallido. Devuelve el conteo actualizado y bloquea si es necesario."""
    key = f"{ip}:{identifier.lower()}"
    now = time.monotonic()
    with _lock:
        rec = _failed_attempts.get(key, {"count": 0, "first": now, "locked_until": 0.0})
        # Reinicia la ventana si el primer intento ya expiró
        if now - rec["first"] > _DUR:
            rec = {"count": 0, "first": now, "locked_until": 0.0}
        rec["count"] += 1
        if rec["count"] >= _MAX:
            rec["locked_until"] = now + _DUR
            logger.warning(
                f"[SECURITY] Login lockout activated — ip={ip} identifier={identifier} "
                f"attempts={rec['count']}"
            )
        _failed_attempts[key] = rec
        return rec["count"]


def clear_failed_login(ip: str, identifier: str) -> None:
    """Limpia los intentos fallidos tras un login exitoso."""
    key = f"{ip}:{identifier.lower()}"
    with _lock:
        _failed_attempts.pop(key, None)


def lockout_remaining_str(seconds: float) -> str:
    """Formatea el tiempo restante de bloqueo para el usuario."""
    minutes = int(seconds // 60)
    secs    = int(seconds % 60)
    if minutes > 0:
        return f"{minutes} min {secs} seg"
    return f"{secs} seg"
