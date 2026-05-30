import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from .config import settings
from .core.rate_limiter import limiter
from .database import database, engine
from .models import metadata
from .routers import cards, decks
from .routers import auth, folders, collection, feedback, admin, admin_panel, legal, bulk_scan

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="One Piece TCG API", version="2.2.0")

# ── Rate limiter ──────────────────────────────────────────────────────────────

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas solicitudes. Espera un momento e intenta de nuevo.",
            "retry_after": str(exc.retry_after) if hasattr(exc, "retry_after") else "60",
        },
        headers={"Retry-After": "60"},
    )

# ── CORS ──────────────────────────────────────────────────────────────────────
# Orígenes desde variable de entorno CORS_ORIGINS (lista separada por comas).
# En producción, define CORS_ORIGINS con los dominios reales.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(cards.router)
app.include_router(decks.router)
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(collection.router)
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(admin_panel.router)
app.include_router(legal.router)
app.include_router(bulk_scan.router)


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
        # Legal — aceptación de términos
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version      VARCHAR(10)               DEFAULT ''",
        # Seguridad — soft delete
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL",
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
    settings.validate_security()   # Valida configuración crítica
    metadata.create_all(engine)    # Crea tablas nuevas (audit_logs, etc.)
    await database.connect()
    await _run_migrations()         # Agrega columnas nuevas a tablas existentes


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/")
async def root():
    return {"status": "ok", "message": "One Piece TCG API v2.1"}
