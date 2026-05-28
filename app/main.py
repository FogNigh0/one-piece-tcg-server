from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import database, engine
from .models import metadata
from .routers import cards, decks
from .routers import auth, folders, collection, feedback, admin, admin_panel


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
    """Agrega columnas nuevas a tablas existentes (idempotente — usa IF NOT EXISTS)."""
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin    BOOLEAN   NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium  BOOLEAN   NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_since TIMESTAMP          DEFAULT NULL",
        "ALTER TABLE user_folders ADD COLUMN IF NOT EXISTS folder_type VARCHAR(20) NOT NULL DEFAULT 'collection'",
    ]
    for sql in migrations:
        try:
            await database.execute(sql)
        except Exception:
            pass


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
