import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import database
from ..models import user_folders, user_folder_cards
from .auth import get_current_user

router = APIRouter(prefix="/folders", tags=["folders"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    name: str

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None

class FolderResponse(BaseModel):
    id: int
    name: str
    user_id: int
    is_public: bool
    share_token: Optional[str]
    created_at: datetime

class FolderCardItem(BaseModel):
    card_set_code: str
    quantity: int

class FolderCardsSync(BaseModel):
    cards: List[FolderCardItem]

class PublicFolderView(BaseModel):
    id: int
    name: str
    owner_username: str
    cards: List[FolderCardItem]
    total_cards: int


# ── CRUD carpetas propias ─────────────────────────────────────────────────────

@router.get("", response_model=List[FolderResponse])
async def list_my_folders(current_user=Depends(get_current_user)):
    rows = await database.fetch_all(
        user_folders.select()
        .where(user_folders.c.user_id == current_user["id"])
        .order_by(user_folders.c.created_at.desc())
    )
    return [dict(r) for r in rows]


@router.post("", response_model=FolderResponse, status_code=201)
async def create_folder(body: FolderCreate, current_user=Depends(get_current_user)):
    folder_id = await database.execute(
        user_folders.insert().values(
            name=body.name.strip(),
            user_id=current_user["id"],
            is_public=False,
        )
    )
    folder = await database.fetch_one(
        user_folders.select().where(user_folders.c.id == folder_id)
    )
    return dict(folder)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    body: FolderUpdate,
    current_user=Depends(get_current_user),
):
    folder = await _get_own_folder(folder_id, current_user["id"])
    values = {}

    if body.name is not None:
        values["name"] = body.name.strip()

    if body.is_public is not None:
        values["is_public"] = body.is_public
        if body.is_public and not folder["share_token"]:
            values["share_token"] = str(uuid.uuid4())
        elif not body.is_public:
            values["share_token"] = None

    if values:
        await database.execute(
            user_folders.update()
            .where(user_folders.c.id == folder_id)
            .values(**values)
        )

    updated = await database.fetch_one(
        user_folders.select().where(user_folders.c.id == folder_id)
    )
    return dict(updated)


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(folder_id: int, current_user=Depends(get_current_user)):
    await _get_own_folder(folder_id, current_user["id"])
    await database.execute(
        user_folders.delete().where(user_folders.c.id == folder_id)
    )


# ── Cartas en carpeta ─────────────────────────────────────────────────────────

@router.get("/{folder_id}/cards", response_model=List[FolderCardItem])
async def get_folder_cards(folder_id: int, current_user=Depends(get_current_user)):
    await _get_own_folder(folder_id, current_user["id"])
    rows = await database.fetch_all(
        user_folder_cards.select()
        .where(user_folder_cards.c.folder_id == folder_id)
    )
    return [{"card_set_code": r["card_set_code"], "quantity": r["quantity"]} for r in rows]


@router.put("/{folder_id}/cards")
async def sync_folder_cards(
    folder_id: int,
    body: FolderCardsSync,
    current_user=Depends(get_current_user),
):
    await _get_own_folder(folder_id, current_user["id"])

    await database.execute(
        user_folder_cards.delete()
        .where(user_folder_cards.c.folder_id == folder_id)
    )
    for item in body.cards:
        await database.execute(
            user_folder_cards.insert().values(
                folder_id=folder_id,
                card_set_code=item.card_set_code,
                quantity=item.quantity,
            )
        )
    return {"synced": len(body.cards)}


# ── Vista pública sin auth ────────────────────────────────────────────────────

@router.get("/public/{share_token}", response_model=PublicFolderView)
async def view_public_folder(share_token: str):
    from ..models import users as users_table

    folder = await database.fetch_one(
        user_folders.select().where(
            (user_folders.c.share_token == share_token) &
            (user_folders.c.is_public == True)
        )
    )
    if not folder:
        raise HTTPException(404, "Carpeta no encontrada o no es pública")

    owner = await database.fetch_one(
        users_table.select().where(users_table.c.id == folder["user_id"])
    )
    cards_rows = await database.fetch_all(
        user_folder_cards.select()
        .where(user_folder_cards.c.folder_id == folder["id"])
    )
    cards = [
        FolderCardItem(card_set_code=r["card_set_code"], quantity=r["quantity"])
        for r in cards_rows
    ]
    return PublicFolderView(
        id=folder["id"],
        name=folder["name"],
        owner_username=owner["username"] if owner else "desconocido",
        cards=cards,
        total_cards=sum(c.quantity for c in cards),
    )


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_own_folder(folder_id: int, user_id: int):
    folder = await database.fetch_one(
        user_folders.select().where(
            (user_folders.c.id == folder_id) &
            (user_folders.c.user_id == user_id)
        )
    )
    if not folder:
        raise HTTPException(404, "Carpeta no encontrada")
    return folder