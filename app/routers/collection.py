from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime

from ..database import database
from ..models import user_collection
from .auth import get_current_user

router = APIRouter(prefix="/collection", tags=["collection"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CollectionCardItem(BaseModel):
    card_set_code: str
    quantity: int

class CollectionSync(BaseModel):
    cards: List[CollectionCardItem]

class CollectionResponse(BaseModel):
    card_set_code: str
    quantity: int
    updated_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CollectionResponse])
async def get_collection(current_user=Depends(get_current_user)):
    rows = await database.fetch_all(
        user_collection.select()
        .where(user_collection.c.user_id == current_user["id"])
        .order_by(user_collection.c.updated_at.desc())
    )
    return [dict(r) for r in rows]


@router.put("/sync")
async def sync_collection(
    body: CollectionSync,
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]

    for item in body.cards:
        existing = await database.fetch_one(
            user_collection.select().where(
                (user_collection.c.user_id == user_id) &
                (user_collection.c.card_set_code == item.card_set_code)
            )
        )
        if existing:
            await database.execute(
                user_collection.update()
                .where(
                    (user_collection.c.user_id == user_id) &
                    (user_collection.c.card_set_code == item.card_set_code)
                )
                .values(quantity=item.quantity, updated_at=datetime.utcnow())
            )
        else:
            await database.execute(
                user_collection.insert().values(
                    user_id=user_id,
                    card_set_code=item.card_set_code,
                    quantity=item.quantity,
                )
            )

    return {"synced": len(body.cards)}


@router.delete("/sync")
async def clear_collection(current_user=Depends(get_current_user)):
    await database.execute(
        user_collection.delete()
        .where(user_collection.c.user_id == current_user["id"])
    )
    return {"deleted": True}