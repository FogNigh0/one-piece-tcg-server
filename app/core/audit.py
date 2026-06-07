# app/core/audit.py
# Registro de auditoría para acciones críticas de seguridad y administración.
# Todas las funciones son fire-and-forget (fallos no interrumpen el flujo).

import json
import logging
from datetime import datetime, timezone
from typing import Any

from ..database import database
from ..models import audit_logs

logger = logging.getLogger("uvicorn.error")


# ── Constantes de acción ──────────────────────────────────────────────────────

class AuditAction:
    # Autenticación
    USER_REGISTER        = "USER_REGISTER"
    USER_LOGIN_SUCCESS   = "USER_LOGIN_SUCCESS"
    USER_LOGIN_FAIL      = "USER_LOGIN_FAIL"
    USER_LOGIN_LOCKED    = "USER_LOGIN_LOCKED"
    USER_DELETE          = "USER_DELETE"          # soft delete (solicitud de eliminación)
    USER_RESTORE         = "USER_RESTORE"         # recuperación durante período de gracia
    USER_PURGE           = "USER_PURGE"           # eliminación definitiva (purga tras gracia)
    USER_PROFILE_UPDATE  = "USER_PROFILE_UPDATE"
    USER_PASSWORD_CHANGE = "USER_PASSWORD_CHANGE"
    USER_EMAIL_CHANGE    = "USER_EMAIL_CHANGE"
    USER_PLAN_REFRESH    = "USER_PLAN_REFRESH"

    # Administración
    ADMIN_BAN_USER       = "ADMIN_BAN_USER"
    ADMIN_UNBAN_USER     = "ADMIN_UNBAN_USER"
    ADMIN_SET_PREMIUM    = "ADMIN_SET_PREMIUM"
    ADMIN_REVOKE_PREMIUM = "ADMIN_REVOKE_PREMIUM"
    ADMIN_DELETE_USER    = "ADMIN_DELETE_USER"

    # Seguridad
    RATE_LIMIT_HIT       = "RATE_LIMIT_HIT"


# ── Función principal ─────────────────────────────────────────────────────────

async def log_audit(
    action: str,
    *,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | str | None = None,
    success: bool = True,
) -> None:
    """
    Registra un evento de auditoría en la base de datos.
    Los errores se loguean pero nunca interrumpen el flujo de negocio.
    """
    try:
        details_str: str | None = None
        if isinstance(details, dict):
            details_str = json.dumps(details, ensure_ascii=False)
        elif isinstance(details, str):
            details_str = details

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        await database.execute(
            audit_logs.insert().values(
                action=action,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                ip_address=ip_address,
                details=details_str,
                success=success,
                timestamp=now_naive,
            )
        )
    except Exception as exc:
        logger.error(f"[AUDIT] Failed to write audit log — action={action}: {exc}")
