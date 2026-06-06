"""
Script OPTIMIZADO de importación de cartas desde optcgapi.com

Mejoras:
  ✓ Mejor manejo de errores y rate limits
  ✓ Validación exhaustiva de datos
  ✓ Progreso visual con ETA
  ✓ Batch commits para mejor performance
  ✓ Detecta sets disponibles automáticamente
  ✓ Logging detallado
  ✓ Reintentos inteligentes con backoff exponencial

Uso:
    python scripts/import_cards_optimized.py
    python scripts/import_cards_optimized.py --sets OP13 OP14 OP15
    python scripts/import_cards_optimized.py --sets OP13-OP15  # rango
"""

import asyncio
import argparse
import httpx
import psycopg2
import os
import sys
import time
from datetime import datetime
from typing import Optional

# ── Configuración ─────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "nozomi.proxy.rlwy.net"),
    "port":     int(os.getenv("DB_PORT", "33325")),
    "dbname":   os.getenv("DB_NAME", "railway"),
    "user":     os.getenv("DB_USER", "postgres"),
    # SIN credencial por defecto: define DB_PASS como variable de entorno.
    "password": os.getenv("DB_PASS", ""),
}

if not DB_CONFIG["password"]:
    raise SystemExit("Falta DB_PASS. Define la variable de entorno antes de ejecutar.")

API_BASE = "https://optcgapi.com/api"
BATCH_SIZE = 50  # commits cada N inserciones
INITIAL_DELAY = 0.3  # segundos entre requests

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_FILE = "import_cards.log"

def log(msg: str, level: str = "INFO"):
    """Registra en consola y archivo."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except:
        pass

# ── Base de datos ─────────────────────────────────────────────────────────────

def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        log(f"Error de conexión a BD: {e}", "ERROR")
        sys.exit(1)

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
        # Índices para búsqueda rápida
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_set ON cards(set_code);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_type ON cards(card_type);")
        conn.commit()
    log("✓ Tabla 'cards' y índices listos")

def upsert_card(cur, card: dict) -> bool:
    """Inserta o actualiza una carta. Retorna True si fue exitosa."""
    try:
        # Validación básica
        if not card.get("id") or not card.get("name") or not card.get("set_code"):
            return False

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
        return True
    except Exception as e:
        log(f"  Error en upsert {card.get('id','?')}: {e}", "WARN")
        return False

# ── Parseo de carta ───────────────────────────────────────────────────────────

def safe_int(val) -> Optional[int]:
    try:
        return int(str(val).replace("-", "").replace("+", "")) if val else None
    except (ValueError, TypeError):
        return None

def parse_card(raw: dict) -> Optional[dict]:
    """Convierte un objeto de la API al formato de nuestra BD."""
    image_id = raw.get("card_image_id", "").strip()
    set_id   = raw.get("card_set_id", "").strip()
    name     = raw.get("card_name", "").strip()

    if not image_id or not set_id or not name:
        return None

    parts    = set_id.split("-")
    set_code = parts[0] if len(parts) >= 2 else set_id
    number   = parts[1] if len(parts) >= 2 else ""

    return {
        "id":        image_id,
        "name":      name,
        "set_code":  set_code,
        "number":    number,
        "card_type": (raw.get("card_type") or "").strip(),
        "color":     (raw.get("card_color") or "").strip(),
        "cost":      safe_int(raw.get("card_cost")),
        "power":     safe_int(raw.get("card_power")),
        "counter":   safe_int(raw.get("counter_amount")),
        "attribute": (raw.get("attribute") or "").strip(),
        "faction":   (raw.get("sub_types") or "").strip(),
        "effect":    (raw.get("card_text") or "").strip(),
        "trigger":   (raw.get("trigger_effect") or "").strip(),
        "rarity":    (raw.get("rarity") or "").strip(),
        "image_url": (raw.get("card_image") or "").strip(),
    }

# ── Obtención de datos con reintentos ─────────────────────────────────────────

async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 5,
    initial_delay: float = 0.5,
) -> Optional[dict]:
    """Fetch con backoff exponencial para rate limits."""
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            resp = await client.get(url, timeout=20)

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                log(f"  ⏳ Rate limit (intento {attempt + 1}/{max_retries}), esperando {delay:.1f}s...", "WARN")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 30)  # max 30s
            else:
                return None
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 30)
        except Exception as e:
            log(f"  Error en {url}: {e}", "WARN")
            return None

    return None

async def fetch_all_sets(client: httpx.AsyncClient) -> set[str]:
    """Detecta automáticamente qué sets están disponibles en la API."""
    data = await fetch_with_retry(client, f"{API_BASE}/allSetCards/")
    if not data:
        return set()

    if not isinstance(data, list):
        data = data.get("cards") or data.get("data") or []

    sets = {card.get("card_set_id", "").split("-")[0]
            for card in data
            if card.get("card_set_id", "")}

    return {s for s in sets if s}  # Filtra vacías

# ── Importación principal ─────────────────────────────────────────────────────

async def import_sets(sets_to_import: list[str]):
    log(f"\n{'='*60}")
    log("  One Piece TCG — Importación OPTIMIZADA con variantes")
    log(f"{'='*60}\n")

    conn = get_connection()
    ensure_table(conn)

    total_cards   = 0
    total_variants = 0
    total_errors = 0
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        # Detecta sets disponibles
        log("Detectando sets disponibles...", "INFO")
        available_sets = await fetch_all_sets(client)

        if not available_sets:
            log("✗ No se encontraron sets en la API", "ERROR")
            conn.close()
            return

        log(f"✓ Sets disponibles: {sorted(available_sets)}\n")

        # Filtra sets a importar que realmente existan
        valid_sets = sorted([s for s in sets_to_import if s in available_sets])
        invalid = [s for s in sets_to_import if s not in available_sets]

        if invalid:
            log(f"⚠ Sets no disponibles (se ignorarán): {', '.join(invalid)}", "WARN")

        if not valid_sets:
            log("✗ Ningún set válido para importar", "ERROR")
            conn.close()
            return

        log(f"Importando: {', '.join(valid_sets)}\n")

        # Descarga índice completo
        log("Descargando índice de cartas...")
        index_data = await fetch_with_retry(client, f"{API_BASE}/allSetCards/")

        if not index_data:
            log("✗ No se pudo descargar el índice", "ERROR")
            conn.close()
            return

        if not isinstance(index_data, list):
            index_data = index_data.get("cards") or index_data.get("data") or []

        log(f"✓ {len(index_data)} entradas en el índice\n")

        # Importa cada set
        for set_code in valid_sets:
            base_ids = sorted({
                c["card_set_id"]
                for c in index_data
                if c.get("card_set_id", "").startswith(set_code + "-")
            })

            if not base_ids:
                log(f"{set_code}: sin cartas encontradas")
                continue

            log(f"[{set_code}] Importando {len(base_ids)} cartas...")
            set_count    = 0
            variant_count = 0
            set_errors = 0

            with conn.cursor() as cur:
                for i, base_id in enumerate(base_ids):
                    # Progreso
                    if (i + 1) % 10 == 0:
                        pct = (i + 1) * 100 // len(base_ids)
                        print(f"  [{pct}%] {i + 1}/{len(base_ids)}", end='\r')

                    # Pausa entre requests
                    if i > 0:
                        await asyncio.sleep(INITIAL_DELAY)

                    # Obtiene todas las versiones
                    versions = await fetch_with_retry(
                        client,
                        f"{API_BASE}/sets/card/{base_id}/",
                        max_retries=3,
                        initial_delay=0.5
                    )

                    if not versions:
                        set_errors += 1
                        continue

                    if not isinstance(versions, list):
                        versions = [versions]

                    for raw in versions:
                        card = parse_card(raw)
                        if not card:
                            continue

                        if upsert_card(cur, card):
                            if "_p" in card["id"]:
                                variant_count += 1
                            else:
                                set_count += 1

                            # Batch commit
                            if (set_count + variant_count) % BATCH_SIZE == 0:
                                conn.commit()
                        else:
                            set_errors += 1

                    # Commit final del set
                    conn.commit()

            elapsed = time.time() - start_time
            log(f"  ✓ {set_count} cartas + {variant_count} variantes ({set_errors} errores) [{elapsed:.1f}s]")

            total_cards    += set_count
            total_variants += variant_count
            total_errors   += set_errors

    elapsed = time.time() - start_time
    conn.close()

    log(f"\n{'='*60}")
    log(f"  Total: {total_cards} cartas + {total_variants} variantes")
    log(f"  Errores: {total_errors}")
    log(f"  Tiempo: {elapsed:.1f}s")
    log(f"{'='*60}\n")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importa cartas de One Piece TCG (OPTIMIZADO)")
    parser.add_argument(
        "--sets", nargs="+",
        help="Sets a importar (ej: --sets OP14 OP13). Detecta automáticamente disponibilidad.",
    )
    args = parser.parse_args()

    if args.sets:
        # Soporta rango: OP13-OP15
        sets = []
        for s in args.sets:
            if "-" in s:
                start, end = s.split("-")
                start_num = int(start[2:])
                end_num = int(end[2:]) if len(end) > 2 else int(end)
                sets.extend([f"{start[:2]}{i:02d}" for i in range(start_num, end_num + 1)])
            else:
                sets.append(s.upper())
    else:
        # KNOWN_SETS original
        sets = [
            "OP01", "OP02", "OP03", "OP04", "OP05", "OP06",
            "OP07", "OP08", "OP09", "OP10", "OP11", "OP12",
            "OP13", "OP14", "OP15",
            "ST01", "ST02", "ST03", "ST04", "ST05", "ST06",
            "ST07", "ST08", "ST09", "ST10", "ST11", "ST12",
            "ST13", "ST14", "ST15", "ST16", "ST17", "ST18",
            "EB01", "EB02",
        ]

    sets = [s.upper() for s in sets]
    asyncio.run(import_sets(sets))
