from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import func, select

from ..database import database
from ..models import users, user_collection, feedback as feedback_table
from .auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Guard: solo admins ────────────────────────────────────────────────────────

async def require_admin(current_user=Depends(get_current_user)):
    if not current_user["is_admin"]:
        raise HTTPException(403, "Acceso denegado — solo administradores")
    return current_user


# ── Schemas ───────────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_users: int
    active_users: int
    premium_users: int
    total_cards_registered: int
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
    total_users = await database.fetch_val(
        select(func.count()).select_from(users)
    )
    active_users = await database.fetch_val(
        select(func.count()).select_from(users).where(users.c.is_active == True)
    )
    premium_users = await database.fetch_val(
        select(func.count()).select_from(users).where(users.c.is_premium == True)
    )
    total_cards = await database.fetch_val(
        select(func.sum(user_collection.c.quantity)).select_from(user_collection)
    )
    total_fb = await database.fetch_val(
        select(func.count()).select_from(feedback_table)
    )
    unread_fb = await database.fetch_val(
        select(func.count()).select_from(feedback_table)
        .where(feedback_table.c.is_read == False)
    )
    return StatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        premium_users=premium_users or 0,
        total_cards_registered=total_cards or 0,
        total_feedback=total_fb or 0,
        unread_feedback=unread_fb or 0,
    )


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
        return {"id": user_id, "is_active": body.is_active}
    except Exception as e:
        raise HTTPException(500, f"Error al actualizar estado del usuario: {str(e)}")


@router.patch("/users/{user_id}/plan")
async def set_user_plan(
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
        # Se ejecuta en un bloque separado para que un fallo aquí no aborte el paso 1
        if body.is_premium:
            try:
                now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                await database.execute(
                    users.update()
                    .where(users.c.id == user_id)
                    .values(premium_since=now_naive)
                )
            except Exception:
                # La columna puede no existir en DBs antiguas — no es crítico
                pass

        return {"id": user_id, "is_premium": body.is_premium}

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
