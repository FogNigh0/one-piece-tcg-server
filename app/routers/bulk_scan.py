# app/routers/bulk_scan.py
# Endpoints para Escaneo Masivo (funcionalidad Premium).
#
# Las sesiones de escaneo viven principalmente en el cliente Flutter.
# El servidor ofrece:
#   · Sesiones ligeras en memoria (supervivencia ante reinicios opcionales)
#   · Endpoint de guardado masivo al servidor (batch save → user_collection)
#   · Gestión de sesiones activas para auditoría

import json
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from ..config import settings
from ..database import database
from ..models import users, user_collection, user_folders, user_folder_cards
from .auth import get_current_user

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/bulk-scan", tags=["bulk-scan"])


# ── Guard: escaneo masivo ─────────────────────────────────────────────────────

async def require_premium(current_user=Depends(get_current_user)):
    # Si el modelo freemium está desactivado (versión gratuita), el escaneo
    # masivo es libre para todos los usuarios.
    if not settings.FREEMIUM_ENABLED:
        return current_user
    if not current_user["is_premium"] and not current_user["is_admin"]:
        raise HTTPException(403, "Escaneo Masivo es una función exclusiva de Premium.")
    return current_user


# ── Sesiones en memoria ───────────────────────────────────────────────────────
# { session_id: { "user_id": int, "cards": list, "created_at": float, "updated_at": float } }

_SESSIONS: dict[str, dict[str, Any]] = {}
_SESSION_TTL_SEC = 3 * 3600   # 3 horas — limpia sesiones inactivas


def _cleanup_stale():
    """Elimina sesiones expiradas para evitar leaks de memoria."""
    now = time.time()
    stale = [sid for sid, s in _SESSIONS.items()
             if now - s.get("updated_at", 0) > _SESSION_TTL_SEC]
    for sid in stale:
        del _SESSIONS[sid]


# ── Schemas ───────────────────────────────────────────────────────────────────

class BulkScanCardItem(BaseModel):
    card_code:      str
    quantity:       int
    is_alternate:   bool = False
    card_name:      str = ""
    card_type:      str = ""
    faction:        str = ""
    color:          str = ""
    image_url:      str | None = None

    @field_validator("card_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("card_code no puede estar vacío")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v < 1 or v > 999:
            raise ValueError("quantity debe estar entre 1 y 999")
        return v


class CreateSessionRequest(BaseModel):
    """Crea o reinicia una sesión de escaneo masivo."""
    pass


class UpdateSessionRequest(BaseModel):
    """Actualiza las cartas de una sesión activa."""
    cards: list[BulkScanCardItem]

    @field_validator("cards")
    @classmethod
    def validate_cards(cls, v: list) -> list:
        if len(v) > 5000:
            raise ValueError("Máximo 5000 cartas por sesión")
        return v


class BulkSaveRequest(BaseModel):
    """Guarda todas las cartas de la sesión en la colección del servidor."""
    folder_id:  int | None = None
    cards:      list[BulkScanCardItem]

    @field_validator("cards")
    @classmethod
    def validate_cards(cls, v: list) -> list:
        if len(v) > 5000:
            raise ValueError("Máximo 5000 cartas por sesión")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
async def create_session(
    _body: CreateSessionRequest = CreateSessionRequest(),
    current_user=Depends(require_premium),
):
    """Crea una nueva sesión de escaneo masivo para el usuario."""
    _cleanup_stale()
    session_id = str(uuid.uuid4())
    now = time.time()
    _SESSIONS[session_id] = {
        "user_id":    current_user["id"],
        "cards":      [],
        "created_at": now,
        "updated_at": now,
    }
    logger.info(f"[BulkScan] Session created — user={current_user['id']} sid={session_id}")
    return {
        "session_id":  session_id,
        "created_at":  datetime.now(timezone.utc).isoformat(),
        "card_count":  0,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user=Depends(require_premium),
):
    """Obtiene el resumen de una sesión activa."""
    session = _SESSIONS.get(session_id)
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(404, "Sesión no encontrada o expirada.")

    cards  = session["cards"]
    total  = sum(c.get("quantity", 1) for c in cards)
    unique = len({c["card_code"] for c in cards})

    return {
        "session_id":   session_id,
        "card_count":   len(cards),
        "total_copies": total,
        "unique_codes": unique,
        "created_at":   datetime.fromtimestamp(
            session["created_at"], timezone.utc).isoformat(),
    }


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    current_user=Depends(require_premium),
):
    """Reemplaza la lista de cartas de una sesión activa."""
    session = _SESSIONS.get(session_id)
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(404, "Sesión no encontrada o expirada.")

    session["cards"]      = [c.model_dump() for c in body.cards]
    session["updated_at"] = time.time()
    return {"updated": True, "card_count": len(session["cards"])}


@router.delete("/sessions/{session_id}", status_code=204)
async def cancel_session(
    session_id: str,
    current_user=Depends(require_premium),
):
    """Cancela y elimina una sesión de escaneo masivo."""
    session = _SESSIONS.get(session_id)
    if session and session["user_id"] == current_user["id"]:
        del _SESSIONS[session_id]
        logger.info(f"[BulkScan] Session cancelled — user={current_user['id']} sid={session_id}")


@router.post("/save")
async def bulk_save(
    body: BulkSaveRequest,
    current_user=Depends(require_premium),
):
    """
    Guarda en lote las cartas escaneadas en la colección del servidor.
    Opera sobre user_collection (no sobre la BD local de Flutter).
    Devuelve un resumen: upserted, errors.
    """
    if not body.cards:
        return {"upserted": 0, "errors": 0, "detail": "Sin cartas para guardar."}

    user_id    = current_user["id"]
    upserted   = 0
    error_list = []
    now_naive  = datetime.now(timezone.utc).replace(tzinfo=None)

    for item in body.cards:
        try:
            existing = await database.fetch_one(
                user_collection.select()
                .where(user_collection.c.user_id == user_id)
                .where(user_collection.c.card_set_code == item.card_code)
            )
            if existing:
                await database.execute(
                    user_collection.update()
                    .where(user_collection.c.user_id == user_id)
                    .where(user_collection.c.card_set_code == item.card_code)
                    .values(
                        quantity=existing["quantity"] + item.quantity,
                        updated_at=now_naive,
                    )
                )
            else:
                await database.execute(
                    user_collection.insert().values(
                        user_id=user_id,
                        card_set_code=item.card_code,
                        quantity=item.quantity,
                        updated_at=now_naive,
                    )
                )
            upserted += 1
        except Exception as exc:
            logger.warning(
                f"[BulkScan] Error saving card {item.card_code} for user {user_id}: {exc}")
            error_list.append(item.card_code)

    logger.info(
        f"[BulkScan] Batch save — user={user_id} "
        f"upserted={upserted} errors={len(error_list)}"
    )
    return {
        "upserted":    upserted,
        "errors":      len(error_list),
        "error_codes": error_list[:20],  # máx 20 para no inflar la respuesta
    }
