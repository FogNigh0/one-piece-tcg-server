from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import func, select, text

from ..database import database
from ..models import users, user_collection, feedback as feedback_table, audit_logs, cards as cards_table
from ..models import user_folders
from .auth import get_current_user
from ..core.audit import log_audit, AuditAction
from ..core.rate_limiter import get_client_ip

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Guard: solo admins ────────────────────────────────────────────────────────

async def require_admin(current_user=Depends(get_current_user)):
    if not current_user["is_admin"]:
        raise HTTPException(403, "Acceso denegado — solo administradores")
    return current_user


# ── Schemas ───────────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    # ── Usuarios ──────────────────────────────────────────────
    total_users: int
    new_users_today: int
    active_users: int
    premium_users: int
    free_users: int
    banned_users: int
    premium_conversion_rate: float   # porcentaje 0-100
    # ── Contenido ─────────────────────────────────────────────
    total_cards_registered: int
    total_folders: int
    # ── Feedback ──────────────────────────────────────────────
    total_feedback: int
    unread_feedback: int


class UserAdminView(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    is_premium: bool
    created_at: datetime


class FeedbackAdminView(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    type: str
    message: str
    is_read: bool
    created_at: datetime


class ToggleUserRequest(BaseModel):
    is_active: bool


class SetPlanRequest(BaseModel):
    is_premium: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def get_stats(_=Depends(require_admin)):
    # Inicio del día en UTC (naive)
    today_start = datetime.combine(date.today(), datetime.min.time())

    total_users, new_today, active_users, premium_users, banned_users = await _run_parallel([
        select(func.count()).select_from(users),
        select(func.count()).select_from(users).where(users.c.created_at >= today_start),
        select(func.count()).select_from(users).where(users.c.is_active == True),
        select(func.count()).select_from(users).where(users.c.is_premium == True),
        select(func.count()).select_from(users).where(users.c.is_active == False),
    ])

    total_cards, total_folders, total_fb, unread_fb = await _run_parallel([
        select(func.sum(user_collection.c.quantity)).select_from(user_collection),
        select(func.count()).select_from(user_folders),
        select(func.count()).select_from(feedback_table),
        select(func.count()).select_from(feedback_table).where(feedback_table.c.is_read == False),
    ])

    total_users   = total_users   or 0
    premium_users = premium_users or 0
    free_users    = max(0, total_users - premium_users)
    conversion    = round(premium_users / total_users * 100, 1) if total_users > 0 else 0.0

    return StatsResponse(
        total_users=total_users,
        new_users_today=new_today or 0,
        active_users=active_users or 0,
        premium_users=premium_users,
        free_users=free_users,
        banned_users=banned_users or 0,
        premium_conversion_rate=conversion,
        total_cards_registered=total_cards or 0,
        total_folders=total_folders or 0,
        total_feedback=total_fb or 0,
        unread_feedback=unread_fb or 0,
    )


async def _run_parallel(queries: list) -> list:
    """Ejecuta múltiples consultas de scalar en secuencia (databases no soporta verdadero paralelo)."""
    return [await database.fetch_val(q) for q in queries]


# ── TCG Stats ─────────────────────────────────────────────────────────────────

@router.get("/tcg-stats")
async def get_tcg_stats(_=Depends(require_admin)) -> dict:
    """Estadísticas TCG: cartas más usadas, líderes, colores y sets."""

    # Top 10 cartas más poseídas (por copias totales en colección)
    top_cards_rows = await database.fetch_all(text("""
        SELECT uc.card_set_code, SUM(uc.quantity) AS total,
               c.name, c.card_type, c.color
        FROM user_collection uc
        LEFT JOIN cards c ON c.id = uc.card_set_code
        GROUP BY uc.card_set_code, c.name, c.card_type, c.color
        ORDER BY total DESC
        LIMIT 10
    """))

    # Top 5 líderes más usados
    top_leaders_rows = await database.fetch_all(text("""
        SELECT uc.card_set_code, SUM(uc.quantity) AS total,
               c.name, c.color, c.faction
        FROM user_collection uc
        JOIN cards c ON c.id = uc.card_set_code
        WHERE UPPER(c.card_type) = 'LEADER'
        GROUP BY uc.card_set_code, c.name, c.color, c.faction
        ORDER BY total DESC
        LIMIT 5
    """))

    # Distribución por color
    color_rows = await database.fetch_all(text("""
        SELECT COALESCE(NULLIF(TRIM(c.color), ''), 'Sin color') AS color,
               SUM(uc.quantity) AS total
        FROM user_collection uc
        JOIN cards c ON c.id = uc.card_set_code
        GROUP BY color
        ORDER BY total DESC
        LIMIT 10
    """))

    # Sets más populares (prefijo del card_set_code)
    set_rows = await database.fetch_all(text("""
        SELECT
            CASE WHEN strpos(uc.card_set_code, '-') > 0
                 THEN substring(uc.card_set_code, 1, strpos(uc.card_set_code, '-') - 1)
                 ELSE uc.card_set_code
            END AS set_prefix,
            SUM(uc.quantity) AS total
        FROM user_collection uc
        GROUP BY set_prefix
        ORDER BY total DESC
        LIMIT 12
    """))

    return {
        "top_cards":   [dict(r) for r in top_cards_rows],
        "top_leaders": [dict(r) for r in top_leaders_rows],
        "by_color":    [dict(r) for r in color_rows],
        "by_set":      [dict(r) for r in set_rows],
    }


# ── System Stats ──────────────────────────────────────────────────────────────

@router.get("/system")
async def get_system_stats(_=Depends(require_admin)) -> dict:
    """Estado del sistema: errores recientes, intentos fallidos, latencia DB."""
    since_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)

    login_fails = await database.fetch_val(
        select(func.count()).select_from(audit_logs)
        .where(audit_logs.c.action == "USER_LOGIN_FAIL")
        .where(audit_logs.c.timestamp >= since_24h)
    )
    lockouts = await database.fetch_val(
        select(func.count()).select_from(audit_logs)
        .where(audit_logs.c.action == "USER_LOGIN_LOCKED")
        .where(audit_logs.c.timestamp >= since_24h)
    )
    rate_limits = await database.fetch_val(
        select(func.count()).select_from(audit_logs)
        .where(audit_logs.c.action == "RATE_LIMIT_HIT")
        .where(audit_logs.c.timestamp >= since_24h)
    )
    new_registrations = await database.fetch_val(
        select(func.count()).select_from(audit_logs)
        .where(audit_logs.c.action == "USER_REGISTER")
        .where(audit_logs.c.timestamp >= since_24h)
    )
    account_deletions = await database.fetch_val(
        select(func.count()).select_from(audit_logs)
        .where(audit_logs.c.action == "USER_DELETE")
        .where(audit_logs.c.timestamp >= since_24h)
    )

    return {
        "server_timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "operational",
        "last_24h": {
            "login_failures":  login_fails or 0,
            "lockouts":        lockouts or 0,
            "rate_limit_hits": rate_limits or 0,
            "registrations":   new_registrations or 0,
            "account_deletions": account_deletions or 0,
        },
    }


@router.get("/users", response_model=List[UserAdminView])
async def list_users(
    page: int = 1,
    limit: int = 50,
    _=Depends(require_admin),
):
    offset = (page - 1) * limit
    rows = await database.fetch_all(
        users.select()
        .order_by(users.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        UserAdminView(
            id=r["id"],
            username=r["username"],
            email=r["email"],
            is_active=r["is_active"],
            is_admin=r["is_admin"],
            is_premium=r["is_premium"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.patch("/users/{user_id}")
async def toggle_user(
    request: Request,
    user_id: int,
    body: ToggleUserRequest,
    current_admin=Depends(require_admin),
):
    if user_id == current_admin["id"]:
        raise HTTPException(400, "No puedes desactivar tu propia cuenta")
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    try:
        await database.execute(
            users.update().where(users.c.id == user_id).values(is_active=body.is_active)
        )
        action = AuditAction.ADMIN_UNBAN_USER if body.is_active else AuditAction.ADMIN_BAN_USER
        await log_audit(
            action,
            actor_user_id=current_admin["id"],
            target_user_id=user_id,
            ip_address=get_client_ip(request),
            details={"username": user["username"], "is_active": body.is_active},
        )
        return {"id": user_id, "is_active": body.is_active}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error al actualizar estado del usuario: {str(e)}")


@router.patch("/users/{user_id}/plan")
async def set_user_plan(
    request: Request,
    user_id: int,
    body: SetPlanRequest,
    current_admin=Depends(require_admin),
):
    """Cambia el plan (Free / Premium) de un usuario."""
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    try:
        # Paso 1 — actualizar is_premium (campo crítico, siempre debe funcionar)
        await database.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(is_premium=body.is_premium)
        )

        # Paso 2 — actualizar premium_since (timezone-naive para TIMESTAMP sin TZ)
        if body.is_premium:
            try:
                now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                await database.execute(
                    users.update()
                    .where(users.c.id == user_id)
                    .values(premium_since=now_naive)
                )
            except Exception:
                pass  # columna puede no existir en DBs antiguas

        action = AuditAction.ADMIN_SET_PREMIUM if body.is_premium else AuditAction.ADMIN_REVOKE_PREMIUM
        await log_audit(
            action,
            actor_user_id=current_admin["id"],
            target_user_id=user_id,
            ip_address=get_client_ip(request),
            details={"username": user["username"], "is_premium": body.is_premium},
        )

        return {"id": user_id, "is_premium": body.is_premium}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error al actualizar el plan: {str(e)}")


@router.get("/feedback", response_model=List[FeedbackAdminView])
async def list_feedback(
    page: int = 1,
    limit: int = 50,
    unread_only: bool = False,
    _=Depends(require_admin),
):
    offset = (page - 1) * limit
    query = (
        feedback_table.select()
        .order_by(feedback_table.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        query = query.where(feedback_table.c.is_read == False)
    rows = await database.fetch_all(query)

    # Obtener usernames en batch
    user_ids = [r["user_id"] for r in rows if r["user_id"]]
    username_map: dict = {}
    if user_ids:
        user_rows = await database.fetch_all(
            users.select().where(users.c.id.in_(user_ids))
        )
        username_map = {r["id"]: r["username"] for r in user_rows}

    return [
        FeedbackAdminView(
            id=r["id"],
            user_id=r["user_id"],
            username=username_map.get(r["user_id"]) if r["user_id"] else None,
            type=r["type"],
            message=r["message"],
            is_read=r["is_read"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.patch("/feedback/{feedback_id}/read")
async def mark_feedback_read(feedback_id: int, _=Depends(require_admin)):
    await database.execute(
        feedback_table.update()
        .where(feedback_table.c.id == feedback_id)
        .values(is_read=True)
    )
    return {"id": feedback_id, "is_read": True}


@router.patch("/feedback/{feedback_id}/unread")
async def mark_feedback_unread(feedback_id: int, _=Depends(require_admin)):
    """Marca un mensaje como no leído."""
    await database.execute(
        feedback_table.update()
        .where(feedback_table.c.id == feedback_id)
        .values(is_read=False)
    )
    return {"id": feedback_id, "is_read": False}


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(feedback_id: int, _=Depends(require_admin)):
    """Elimina un mensaje de feedback permanentemente."""
    row = await database.fetch_one(
        feedback_table.select().where(feedback_table.c.id == feedback_id)
    )
    if not row:
        raise HTTPException(404, "Mensaje no encontrado")
    await database.execute(
        feedback_table.delete().where(feedback_table.c.id == feedback_id)
    )
    return {"id": feedback_id, "deleted": True}


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLogView(BaseModel):
    id: int
    timestamp: datetime
    action: str
    actor_user_id: Optional[int]
    target_user_id: Optional[int]
    ip_address: Optional[str]
    details: Optional[str]
    success: bool


@router.get("/audit-logs", response_model=List[AuditLogView])
async def get_audit_logs(
    page: int = 1,
    limit: int = 50,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    _=Depends(require_admin),
):
    """Consulta el registro de auditoría. Filtrable por acción y usuario."""
    limit = min(limit, 200)  # máximo 200 por página
    offset = (page - 1) * limit

    query = audit_logs.select().order_by(audit_logs.c.timestamp.desc()).limit(limit).offset(offset)

    if action:
        query = query.where(audit_logs.c.action == action.upper())
    if user_id:
        from sqlalchemy import or_
        query = query.where(
            or_(
                audit_logs.c.actor_user_id == user_id,
                audit_logs.c.target_user_id == user_id,
            )
        )

    rows = await database.fetch_all(query)
    return [
        AuditLogView(
            id=r["id"],
            timestamp=r["timestamp"],
            action=r["action"],
            actor_user_id=r["actor_user_id"],
            target_user_id=r["target_user_id"],
            ip_address=r["ip_address"],
            details=r["details"],
            success=bool(r["success"]),
        )
        for r in rows
    ]
