# app/core/account_purge.py
# Purga definitiva de cuentas en estado "pending_deletion" cuyo período de
# gracia ya venció. Elimina todos los datos personales del usuario; conserva
# únicamente registros de auditoría (sin FK a users, por id, sin PII).

import asyncio
import logging
from datetime import datetime, timedelta

from ..config import settings
from ..database import database
from ..models import (
    users,
    user_folders,
    user_folder_cards,
    user_collection,
    feedback,
)
from .audit import log_audit, AuditAction

logger = logging.getLogger("uvicorn.error")

# Cada cuánto corre la tarea periódica de purga (segundos). 24 h por defecto.
_PURGE_INTERVAL_SEC = 24 * 3600


async def purge_expired_accounts() -> int:
    """Elimina definitivamente las cuentas cuyo período de gracia venció.

    Devuelve el número de cuentas purgadas.
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)

    expired = await database.fetch_all(
        users.select().where(
            (users.c.is_active == False) &           # noqa: E712
            (users.c.deleted_at.isnot(None)) &
            (users.c.deleted_at < cutoff)
        )
    )

    count = 0
    for u in expired:
        uid = u["id"]
        try:
            async with database.transaction():
                # Hijos explícitos (defensivo; el esquema además define CASCADE).
                folder_rows = await database.fetch_all(
                    user_folders.select().where(user_folders.c.user_id == uid)
                )
                folder_ids = [f["id"] for f in folder_rows]
                if folder_ids:
                    await database.execute(
                        user_folder_cards.delete().where(
                            user_folder_cards.c.folder_id.in_(folder_ids)
                        )
                    )
                await database.execute(
                    user_folders.delete().where(user_folders.c.user_id == uid)
                )
                await database.execute(
                    user_collection.delete().where(user_collection.c.user_id == uid)
                )
                # Anonimiza feedback (conserva el mensaje, sin vincular al usuario).
                await database.execute(
                    feedback.update().where(feedback.c.user_id == uid).values(user_id=None)
                )
                # Finalmente, elimina la cuenta.
                await database.execute(users.delete().where(users.c.id == uid))

            await log_audit(
                AuditAction.USER_PURGE, target_user_id=uid, success=True,
                details={"grace_days": settings.ACCOUNT_DELETION_GRACE_DAYS},
            )
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error purgando cuenta id={uid}: {e}")

    if count:
        logger.info(f"Account purge: {count} cuenta(s) eliminada(s) definitivamente")
    return count


async def purge_loop():
    """Tarea de fondo: corre la purga al iniciar y luego periódicamente."""
    while True:
        try:
            await purge_expired_accounts()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error en purge_loop: {e}")
        await asyncio.sleep(_PURGE_INTERVAL_SEC)
