"""
Script de importación de cartas desde optcgapi.com
Usa el endpoint /api/sets/card/{id}/ para obtener TODAS las versiones
(arte normal + arte alternativo + parallel) de cada carta.

Uso:
    python scripts/import_cards.py

Para reimportar un set específico:
    python scripts/import_cards.py --sets OP14

Para agregar sets nuevos, añade el código a KNOWN_SETS.
"""

import asyncio
import argparse
import httpx
import psycopg2
import os

# ── Configuración ─────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "nozomi.proxy.rlwy.net"),
    "port":     int(os.getenv("DB_PORT", "33325")),
    "dbname":   os.getenv("DB_NAME", "railway"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "apthEUgfIwXgLEazqMNGwNxMtDeTDEyf"),
}

API_BASE = "https://optcgapi.com/api"

# Sets a importar — agrega nuevos sets aquí cuando salgan
KNOWN_SETS = [
    "OP01", "OP02", "OP03", "OP04", "OP05", "OP06",
    "OP07", "OP08", "OP09", "OP10", "OP11", "OP12",
    "OP13", "OP14", "OP15",
    "ST01", "ST02", "ST03", "ST04", "ST05", "ST06",
    "ST07", "ST08", "ST09", "ST10", "ST11", "ST12",
    "ST13", "ST14", "ST15", "ST16", "ST17", "ST18",
    "EB01", "EB02",
]

# ── Base de datos ─────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id          VARCHAR PRIMARY KEY,
                name        VARCHAR NOT NULL,
                set_code    VARCHAR NOT NULL,
                number      VARCHAR NOT NULL,
                card_type   VARCHAR,
                color       VARCHAR,
                cost        INTEGER,
                power       INTEGER,
                counter     INTEGER,
                attribute   VARCHAR,
                faction     VARCHAR,
                effect      TEXT,
                trigger     TEXT,
                rarity      VARCHAR,
                image_url   VARCHAR,
                updated_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    print("✓ Tabla 'cards' lista")


def upsert_card(cur, card: dict):
    cur.execute("""
        INSERT INTO cards
            (id, name, set_code, number, card_type, color,
             cost, power, counter, attribute, faction,
             effect, trigger, rarity, image_url, updated_at)
        VALUES
            (%(id)s, %(name)s, %(set_code)s, %(number)s, %(card_type)s, %(color)s,
             %(cost)s, %(power)s, %(counter)s, %(attribute)s, %(faction)s,
             %(effect)s, %(trigger)s, %(rarity)s, %(image_url)s, NOW())
        ON CONFLICT (id) DO UPDATE SET
            name       = EXCLUDED.name,
            card_type  = EXCLUDED.card_type,
            color      = EXCLUDED.color,
            cost       = EXCLUDED.cost,
            power      = EXCLUDED.power,
            counter    = EXCLUDED.counter,
            attribute  = EXCLUDED.attribute,
            faction    = EXCLUDED.faction,
            effect     = EXCLUDED.effect,
            trigger    = EXCLUDED.trigger,
            rarity     = EXCLUDED.rarity,
            image_url  = EXCLUDED.image_url,
            updated_at = NOW()
    """, card)


# ── Parseo de carta ───────────────────────────────────────────────────────────

def safe_int(val):
    try:
        return int(str(val).replace("-", "").replace("+", ""))
    except (ValueError, TypeError):
        return None


def parse_card(raw: dict) -> dict | None:
    """
    Convierte un objeto de la API al formato de nuestra BD.

    La API devuelve:
      card_image_id: "OP14-091"       → arte normal  → ID en BD: "OP14-091"
      card_image_id: "OP14-091_p1"    → arte alt     → ID en BD: "OP14-091_p1"
      card_set_id:   "OP14-091"       → siempre el código base

    Usamos card_image_id como PRIMARY KEY para distinguir variantes.
    """
    image_id = raw.get("card_image_id", "").strip()
    set_id   = raw.get("card_set_id", "").strip()

    if not image_id or not set_id:
        return None

    # set_code y number siempre vienen del card_set_id base (OP14-091)
    parts    = set_id.split("-")
    set_code = parts[0] if len(parts) >= 2 else set_id
    number   = parts[1] if len(parts) >= 2 else ""

    return {
        "id":        image_id,          # OP14-091 o OP14-091_p1
        "name":      raw.get("card_name", "").strip(),
        "set_code":  set_code,          # OP14
        "number":    number,            # 091
        "card_type": raw.get("card_type", ""),
        "color":     raw.get("card_color", ""),
        "cost":      safe_int(raw.get("card_cost")),
        "power":     safe_int(raw.get("card_power")),
        "counter":   safe_int(raw.get("counter_amount")),
        "attribute": raw.get("attribute", ""),
        "faction":   raw.get("sub_types", ""),
        "effect":    raw.get("card_text", ""),
        "trigger":   raw.get("trigger_effect", "") or "",
        "rarity":    raw.get("rarity", ""),
        "image_url": raw.get("card_image", ""),
    }


# ── Obtención de IDs del set ──────────────────────────────────────────────────

async def fetch_set_card_ids(client: httpx.AsyncClient, set_code: str) -> list[str]:
    """
    Obtiene todos los IDs base de un set usando /allSetCards/ filtrado por set_code.
    Devuelve lista de card_set_id únicos (ej: ["OP14-001", "OP14-002", ...])
    """
    try:
        resp = await client.get(f"{API_BASE}/allSetCards/", timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            data = data.get("cards") or data.get("data") or []

        # Filtra por set y obtiene IDs únicos (card_set_id, no card_image_id)
        ids = list({
            card["card_set_id"]
            for card in data
            if card.get("card_set_id", "").startswith(set_code + "-")
        })
        ids.sort()
        return ids
    except Exception as e:
        print(f"  ⚠ Error obteniendo IDs de {set_code}: {e}")
        return []


async def fetch_all_versions(client: httpx.AsyncClient, card_id: str) -> list[dict]:
    """
    Llama a /api/sets/card/{card_id}/ que devuelve TODAS las versiones
    (arte normal + alternate art + parallel) de una carta.
    """
    try:
        resp = await client.get(
            f"{API_BASE}/sets/card/{card_id}/",
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else [data]
    except Exception:
        pass
    return []


# ── Importación principal ─────────────────────────────────────────────────────

async def fetch_all_versions_with_retry(client: httpx.AsyncClient, card_id: str, retries: int = 3) -> list[dict]:
    """Llama al endpoint con reintentos en caso de rate limit (429)."""
    for attempt in range(retries):
        try:
            resp = await client.get(
                f"{API_BASE}/sets/card/{card_id}/",
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else [data]
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  ⏳ Rate limit en {card_id}, esperando {wait}s...", flush=True)
                await asyncio.sleep(wait)
            else:
                return []
        except Exception:
            await asyncio.sleep(2)
    return []


async def import_sets(sets_to_import: list[str]):
    print(f"\n{'='*52}")
    print("  One Piece TCG — Importación completa con variantes")
    print(f"{'='*52}\n")

    conn = get_connection()
    ensure_table(conn)

    total_cards   = 0
    total_variants = 0

    async with httpx.AsyncClient() as client:
        # Descarga lista completa una sola vez para extraer IDs por set
        print("Descargando índice de cartas...", flush=True)
        try:
            resp = await client.get(f"{API_BASE}/allSetCards/", timeout=60)
            resp.raise_for_status()
            all_data = resp.json()
            if not isinstance(all_data, list):
                all_data = all_data.get("cards") or all_data.get("data") or []
            print(f"✓ {len(all_data)} entradas en el índice\n")
        except Exception as e:
            print(f"✗ No se pudo descargar el índice: {e}")
            return

        for set_code in sets_to_import:
            # IDs únicos del set (card_set_id, ej: OP14-091)
            base_ids = sorted({
                c["card_set_id"]
                for c in all_data
                if c.get("card_set_id", "").startswith(set_code + "-")
            })

            if not base_ids:
                print(f"{set_code}: sin cartas en el índice, saltando.")
                continue

            print(f"Importando {set_code} ({len(base_ids)} cartas)...", flush=True)
            set_count    = 0
            variant_count = 0

            with conn.cursor() as cur:
                for i, base_id in enumerate(base_ids):
                    # Pausa entre llamadas para respetar el rate limit
                    if i > 0:
                        await asyncio.sleep(0.4)

                    # Obtiene TODAS las versiones con reintentos
                    versions = await fetch_all_versions_with_retry(client, base_id)

                    for raw in versions:
                        card = parse_card(raw)
                        if not card or not card["name"]:
                            continue
                        try:
                            upsert_card(cur, card)
                            if "_p" in card["id"]:
                                variant_count += 1
                            else:
                                set_count += 1
                        except Exception as e:
                            print(f"\n  ⚠ Error en {card.get('id','?')}: {e}")

                conn.commit()

            print(f"  ✓ {set_count} cartas + {variant_count} variantes (alt art / parallel)")
            total_cards    += set_count
            total_variants += variant_count

    conn.close()
    print(f"\n{'='*52}")
    print(f"  Total: {total_cards} cartas + {total_variants} variantes")
    print(f"{'='*52}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importa cartas de One Piece TCG")
    parser.add_argument(
        "--sets", nargs="+",
        help="Sets a importar (ej: --sets OP14 OP13). Si no se indica, importa todos.",
    )
    args = parser.parse_args()

    sets = args.sets if args.sets else KNOWN_SETS
    sets = [s.upper() for s in sets]

    asyncio.run(import_sets(sets))