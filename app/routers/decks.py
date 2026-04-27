from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import database
from ..models import cards, decks
import re

router = APIRouter(prefix="/decks", tags=["decks"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class DeckCreate(BaseModel):
    name: str
    cards_text: str   # "3xOP05-082 1xOP11-097 4xOP14-079"


class DeckUpdate(BaseModel):
    name: Optional[str] = None
    cards_text: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_deck_text(text: str) -> list[dict]:
    """
    Parsea texto tipo "3xOP05-082 1xOP11-097" a lista de dicts.
    Acepta separadores de espacio, coma o salto de línea.
    """
    entries = []
    # Busca todos los tokens con formato NxXXNN-NNN
    matches = re.findall(r'(\d+)x([A-Za-z0-9]+-\d+)', text)
    for qty_str, card_id in matches:
        entries.append({
            "quantity": int(qty_str),
            "card_id": card_id.upper(),
        })
    return entries


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/resolve")
async def resolve_deck(body: DeckCreate):
    """
    Recibe texto de mazo y devuelve los datos completos de cada carta.
    No guarda nada — solo resuelve los códigos.

    Body: { "name": "Mi mazo", "cards_text": "3xOP05-082 1xOP11-097" }
    """
    entries = parse_deck_text(body.cards_text)

    if not entries:
        raise HTTPException(status_code=400, detail="No se encontraron cartas en el texto")

    resolved = []
    not_found = []

    for entry in entries:
        query = cards.select().where(cards.c.id == entry["card_id"])
        card = await database.fetch_one(query)

        if card:
            resolved.append({
                "quantity": entry["quantity"],
                "card": dict(card),
            })
        else:
            not_found.append(entry["card_id"])

    return {
        "name": body.name,
        "resolved": resolved,
        "not_found": not_found,
        "total_cards": sum(e["quantity"] for e in entries),
    }


@router.post("/")
async def save_deck(body: DeckCreate):
    """
    Guarda un mazo en la base de datos.
    Body: { "name": "Mazo Luffy", "cards_text": "3xOP05-082 1xOP11-097" }
    """
    entries = parse_deck_text(body.cards_text)
    if not entries:
        raise HTTPException(status_code=400, detail="No se encontraron cartas en el texto")

    query = decks.insert().values(name=body.name, cards_text=body.cards_text.strip())
    deck_id = await database.execute(query)

    return {"id": deck_id, "name": body.name, "message": "Mazo guardado"}


@router.get("/")
async def list_decks():
    """Devuelve todos los mazos guardados."""
    query = decks.select().order_by(decks.c.created_at.desc())
    results = await database.fetch_all(query)
    return {"decks": [dict(r) for r in results]}


@router.get("/{deck_id}")
async def get_deck(deck_id: int):
    """Devuelve un mazo con sus cartas resueltas."""
    query = decks.select().where(decks.c.id == deck_id)
    deck = await database.fetch_one(query)

    if deck is None:
        raise HTTPException(status_code=404, detail="Mazo no encontrado")

    deck_dict = dict(deck)
    entries = parse_deck_text(deck_dict["cards_text"])

    resolved = []
    for entry in entries:
        card_query = cards.select().where(cards.c.id == entry["card_id"])
        card = await database.fetch_one(card_query)
        if card:
            resolved.append({"quantity": entry["quantity"], "card": dict(card)})

    return {**deck_dict, "cards": resolved}


@router.put("/{deck_id}")
async def update_deck(deck_id: int, body: DeckUpdate):
    """Actualiza nombre o cartas de un mazo."""
    query = decks.select().where(decks.c.id == deck_id)
    existing = await database.fetch_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Mazo no encontrado")

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.cards_text is not None:
        updates["cards_text"] = body.cards_text.strip()

    if updates:
        await database.execute(decks.update().where(decks.c.id == deck_id).values(**updates))

    return {"message": "Mazo actualizado"}


@router.delete("/{deck_id}")
async def delete_deck(deck_id: int):
    """Elimina un mazo."""
    await database.execute(decks.delete().where(decks.c.id == deck_id))
    return {"message": "Mazo eliminado"}
