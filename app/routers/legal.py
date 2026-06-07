# app/routers/legal.py
# Endpoints legales públicos — versiones de políticas, DMCA y eliminación de cuenta.
# El contenido real de cada documento vive en el cliente (Flutter).

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config import settings

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
        "app_name": "Nakama Cards",
        "disclaimer": (
            "Nakama Cards es una aplicación no oficial creada por fans y no está "
            "afiliada ni respaldada por Bandai, Toei Animation ni los propietarios "
            "de One Piece Card Game. Todas las marcas e imágenes pertenecen a sus "
            "respectivos propietarios."
        ),
    }


@router.get("/account-deletion", response_class=HTMLResponse)
async def account_deletion_page():
    """Página pública (sin login) que explica cómo eliminar la cuenta y los datos.
    Requisito de Google Play: URL accesible sin necesidad de la app."""
    grace = settings.ACCOUNT_DELETION_GRACE_DAYS
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eliminación de cuenta — Nakama Cards</title>
  <style>
    body {{ font-family: system-ui, 'Segoe UI', sans-serif; background:#0A0A0F; color:#EDEDED;
            max-width:720px; margin:0 auto; padding:32px 20px; line-height:1.6; }}
    h1 {{ color:#D4A843; font-size:24px; }}
    h2 {{ color:#D4A843; font-size:17px; margin-top:28px; }}
    code {{ background:#1c1c24; padding:2px 6px; border-radius:5px; }}
    a {{ color:#D4A843; }}
    .card {{ background:#15151c; border:1px solid #2a2a35; border-radius:12px; padding:16px 20px; margin-top:16px; }}
    ul {{ padding-left:20px; }}
  </style>
</head>
<body>
  <h1>Eliminación de cuenta y datos — Nakama Cards</h1>
  <p>Nakama Cards es una aplicación gratuita para coleccionistas de One Piece Card Game.
     Puedes solicitar la eliminación de tu cuenta y de todos tus datos en cualquier momento.</p>

  <h2>Cómo eliminar tu cuenta desde la app</h2>
  <div class="card">
    <ol>
      <li>Abre la app e inicia sesión.</li>
      <li>Ve a <code>Perfil → Seguridad → Eliminar cuenta</code>.</li>
      <li>Confirma con tu contraseña.</li>
    </ol>
  </div>

  <h2>Qué ocurre al solicitar la eliminación</h2>
  <ul>
    <li>Tu cuenta queda <strong>inmediatamente inaccesible</strong> y se cierra la sesión en todos los dispositivos.</li>
    <li>Tienes un período de gracia de <strong>{grace} días</strong> para recuperarla: basta con volver a iniciar sesión con tus credenciales.</li>
    <li>Transcurridos los {grace} días, se eliminan <strong>definitivamente</strong>: tu cuenta, perfil, colección, carpetas, mazos, estadísticas y mensajes asociados.</li>
    <li>Solo se conservan registros técnicos de auditoría anonimizados, sin datos personales.</li>
  </ul>

  <h2>¿No puedes acceder a la app?</h2>
  <p>Si no puedes iniciar sesión, solicita la eliminación escribiendo a
     <a href="mailto:privacidad@nakamacards.app?subject=[Eliminación%20de%20cuenta]">privacidad@nakamacards.app</a>
     con el asunto <code>[Eliminación de cuenta]</code> e indica tu nombre de usuario o correo registrado.
     Procesaremos la solicitud en un plazo de hasta 14 días hábiles.</p>

  <p style="margin-top:32px; font-size:13px; color:#888;">
     Nakama Cards es una aplicación no oficial creada por fans, sin afiliación con Bandai,
     Toei Animation ni los propietarios de One Piece.</p>
</body>
</html>"""


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
