import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import database, engine
from .models import metadata
from .routers import cards, decks
from .routers import auth, folders, collection, feedback, admin, admin_panel

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="One Piece TCG API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(decks.router)
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(collection.router)
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(admin_panel.router)


async def _run_migrations():
    """Agrega columnas nuevas a tablas existentes (idempotente — usa IF NOT EXISTS).
    Los errores se loguean en lugar de ignorarse en silencio."""
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin      BOOLEAN   NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium    BOOLEAN   NOT NULL DEFAULT false",
        # TIMESTAMP WITHOUT TIME ZONE — acepta valores timezone-naive de Python
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_since TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL",
        "ALTER TABLE user_folders ADD COLUMN IF NOT EXISTS folder_type VARCHAR(20) NOT NULL DEFAULT 'collection'",
        # Perfil de usuario — bio y avatar
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio    VARCHAR(150) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR(20)  DEFAULT ''",
    ]
    for sql in migrations:
        try:
            await database.execute(sql)
            logger.info(f"Migration OK: {sql[:60]}…")
        except Exception as exc:
            # "column already exists" es esperado en reinicios — el resto son errores reales
            msg = str(exc).lower()
            if "already exists" in msg or "duplicate column" in msg:
                pass  # idempotente — columna ya existía
            else:
                logger.error(f"Migration FAILED: {sql[:60]}… → {exc}")


@app.on_event("startup")
async def startup():
    metadata.create_all(engine)   # Crea tablas nuevas (feedback, etc.)
    await database.connect()
    await _run_migrations()        # Agrega columnas nuevas a tablas existentes


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/")
async def root():
    return {"status": "ok", "message": "One Piece TCG API v2.1"}
