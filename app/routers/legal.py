# app/routers/legal.py
# Endpoints legales públicos — versiones de políticas y DMCA.
# El contenido real de cada documento vive en el cliente (Flutter).

from fastapi import APIRouter

router = APIRouter(prefix="/legal", tags=["legal"])

# ── Constantes de versión ─────────────────────────────────────────────────────

TERMS_VERSION     = "v1.0"
TERMS_UPDATED     = "2025-01-01"
PRIVACY_VERSION   = "v1.0"
PRIVACY_UPDATED   = "2025-01-01"
PREMIUM_VERSION   = "v1.0"
PREMIUM_UPDATED   = "2025-01-01"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/versions")
async def get_legal_versions():
    """Devuelve las versiones actuales de todas las políticas legales.
    El cliente usa esto para saber si el usuario necesita re-aceptar términos."""
    return {
        "terms": {
            "version": TERMS_VERSION,
            "updated": TERMS_UPDATED,
        },
        "privacy": {
            "version": PRIVACY_VERSION,
            "updated": PRIVACY_UPDATED,
        },
        "premium": {
            "version": PREMIUM_VERSION,
            "updated": PREMIUM_UPDATED,
        },
        "app_name": "NakamaCards",
        "disclaimer": (
            "NakamaCards es una aplicación no oficial creada por fans y no está "
            "afiliada ni respaldada por Bandai, Toei Animation ni los propietarios "
            "de One Piece Card Game. Todas las marcas e imágenes pertenecen a sus "
            "respectivos propietarios."
        ),
    }


@router.get("/dmca")
async def get_dmca_info():
    """Información de contacto para reclamos DMCA / copyright."""
    return {
        "contact_email": "legal@nakamacards.app",
        "subject_prefix": "[DMCA]",
        "response_time_days": 14,
        "process": [
            "Envía tu reclamo a legal@nakamacards.app con asunto [DMCA].",
            "Incluye: descripción del contenido, URL o identificador, prueba de propiedad.",
            "Revisamos el reclamo en un plazo de hasta 14 días hábiles.",
            "Notificamos la decisión y, si procede, eliminamos el contenido.",
        ],
    }
