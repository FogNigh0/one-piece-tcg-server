from fastapi import APIRouter, HTTPException
from ..database import database
from ..models import cards
import sqlalchemy

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/")
async def search_cards(
    q: str = "",
    set_code: str = "",
    card_type: str = "",
    color: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """
    Búsqueda general de cartas con filtros opcionales.
    Ejemplos:
      GET /cards/?q=Luffy
      GET /cards/?set_code=OP14
      GET /cards/?color=Red&card_type=CHARACTER
    """
    query = cards.select()

    if q:
        query = query.where(cards.c.name.ilike(f"%{q}%"))
    if set_code:
        query = query.where(cards.c.set_code == set_code.upper())
    if card_type:
        query = query.where(cards.c.card_type == card_type.upper())
    if color:
        query = query.where(cards.c.color.ilike(f"%{color}%"))

    query = query.limit(limit).offset(offset)
    results = await database.fetch_all(query)
    return {"results": [dict(r) for r in results], "count": len(results)}


@router.get("/set/{set_code}")
async def get_set(set_code: str):
    """
    Devuelve todas las cartas de un set.
    Ejemplo: GET /cards/set/OP14
    """
    set_code = set_code.upper()
    query = cards.select().where(cards.c.set_code == set_code).order_by(cards.c.number)
    results = await database.fetch_all(query)

    if not results:
        raise HTTPException(status_code=404, detail=f"Set {set_code} no encontrado")

    return {"set": set_code, "cards": [dict(r) for r in results]}


# IMPORTANTE: esta ruta va SIEMPRE al final porque {card_id:path} es muy
# greedy y capturaría /set/OP14 y / si fuera primero.
@router.get("/{card_id:path}")
async def get_card(card_id: str):
    """
    Busca una carta por su código exacto.
    Acepta IDs con sufijos de variante como OP14-091_p1.
    Ejemplo: GET /cards/OP14-079
             GET /cards/OP14-091_p1
    """
    # Normaliza el código base a mayúsculas pero preserva el sufijo de variante
    # Ej: "op14-091_p1" → "OP14-091_p1"  (NO "OP14-091_P1")
    if "_p" in card_id.lower():
        parts = card_id.lower().split("_p", 1)
        card_id = parts[0].upper() + "_p" + parts[1]
    else:
        card_id = card_id.upper().strip()

    query = cards.select().where(cards.c.id == card_id)
    card = await database.fetch_one(query)

    if card is None:
        raise HTTPException(status_code=404, detail=f"Carta {card_id} no encontrada")

    return dict(card)
