import re
import logging
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

import re as _re
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..core.rate_limiter import (
    limiter, get_client_ip,
    is_login_locked, record_failed_login, clear_failed_login, lockout_remaining_str,
)
from ..core.audit import log_audit, AuditAction


def _sanitize(value: str | None) -> str:
    """Elimina etiquetas HTML y normaliza espacios en blanco."""
    if not value:
        return value or ""
    value = _re.sub(r'<[^>]+>', '', value)          # elimina HTML tags
    value = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)  # elimina control chars
    return ' '.join(value.split())                   # normaliza espacios
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import func

from ..database import database
from ..models import users
from ..config import settings
from ..core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from jose import jwt, JWTError

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    terms_accepted: bool = False   # debe ser True para crear cuenta

    @field_validator("terms_accepted")
    @classmethod
    def must_accept_terms(cls, v):
        if not v:
            raise ValueError("Debes aceptar los Términos y Condiciones para registrarte")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Mínimo 3 caracteres")
        if len(v) > 20:
            raise ValueError("Máximo 20 caracteres")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Solo letras, números y guión bajo (_)")
        return v

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v):
        return v.lower().strip() if v else v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 8:
            raise ValueError("Mínimo 8 caracteres")
        if not re.search(r'[0-9]', v):
            raise ValueError("Debe contener al menos un número")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', v):
            raise ValueError("Debe contener al menos un carácter especial")
        return v


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 8:
            raise ValueError("Mínimo 8 caracteres")
        if not re.search(r'[0-9]', v):
            raise ValueError("Debe contener al menos un número")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', v):
            raise ValueError("Debe contener al menos un carácter especial")
        return v


class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    is_premium: bool = False
    created_at: datetime
    bio: str = ''
    avatar: str = ''


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Mínimo 3 caracteres")
        if len(v) > 20:
            raise ValueError("Máximo 20 caracteres")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Solo letras, números y guión bajo (_)")
        return v

    @field_validator("bio")
    @classmethod
    def bio_valid(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 150:
            raise ValueError("Máximo 150 caracteres")
        return v

    @field_validator("avatar")
    @classmethod
    def avatar_valid(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Avatar inválido")
        return v

    @field_validator("new_password")
    @classmethod
    def new_password_valid(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Mínimo 8 caracteres")
        if not re.search(r'[0-9]', v):
            raise ValueError("Debe contener al menos un número")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', v):
            raise ValueError("Debe contener al menos un carácter especial")
        return v


class DeleteAccountRequest(BaseModel):
    password: str


# ── get_current_user ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Token inválido o expirado")
    user = await database.fetch_one(
        users.select().where(users.c.id == int(payload["sub"]))
    )
    if not user or not user["is_active"]:
        raise HTTPException(401, "Usuario no encontrado")
    return user


# ── Email helper ──────────────────────────────────────────────────────────────

def _send_email_sync(to: str, subject: str, html_body: str) -> None:
    if not settings.SMTP_FROM or not settings.SMTP_PASSWORD:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_FROM, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to, msg.as_string())


async def send_email(to: str, subject: str, html_body: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_email_sync, to, subject, html_body)


def _create_reset_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "type": "reset", "exp": expire},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(row, key: str, default='') -> str:
    """Lee un campo opcional del row con fallback seguro."""
    try:
        return row[key] or default
    except (KeyError, TypeError):
        return default


def _to_user_public(row) -> UserPublic:
    """Construye UserPublic desde un registro de DB incluyendo campos opcionales."""
    return UserPublic(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        is_premium=bool(row["is_premium"]) if row["is_premium"] is not None else False,
        created_at=row["created_at"],
        bio=_safe(row, "bio"),
        avatar=_safe(row, "avatar"),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest):
    ip = get_client_ip(request)
    try:
        # 1. Unicidad de email
        existing_email = await database.fetch_one(
            users.select().where(users.c.email == body.email.lower().strip())
        )
        if existing_email:
            await log_audit(AuditAction.USER_REGISTER, ip_address=ip, success=False,
                            details={"reason": "email_taken", "email": body.email})
            raise HTTPException(400, "El email ya está registrado")

        # 2. Unicidad de username (case-insensitive)
        existing_user = await database.fetch_one(
            users.select().where(
                func.lower(users.c.username) == body.username.strip().lower()
            )
        )
        if existing_user:
            await log_audit(AuditAction.USER_REGISTER, ip_address=ip, success=False,
                            details={"reason": "username_taken", "username": body.username.strip()})
            raise HTTPException(400, "El nombre de usuario ya está en uso")

        # 3. Insertar usuario — is_premium se especifica explícitamente para evitar
        #    problemas si la columna fue agregada por migración sin DEFAULT en el DB real
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        user_id = await database.execute(
            users.insert().values(
                username=body.username.strip(),
                email=body.email.lower().strip(),
                password_hash=hash_password(body.password),
                is_active=True,
                is_admin=False,
                is_premium=False,
                terms_accepted_at=now_naive if body.terms_accepted else None,
                terms_version="v1.0"        if body.terms_accepted else "",
            )
        )
        logger.info(f"New user registered — id={user_id}, username={body.username.strip()}")
        await log_audit(AuditAction.USER_REGISTER, actor_user_id=user_id,
                        ip_address=ip, success=True,
                        details={"username": body.username.strip()})

        # 4. Recuperar el usuario recién creado
        new_user = await database.fetch_one(
            users.select().where(users.c.id == user_id)
        )
        if new_user is None:
            logger.error(f"User inserted but not found — user_id={user_id}")
            raise HTTPException(500, "Error al crear la cuenta. Intenta de nuevo.")

        # 5. Leer is_premium con fallback por si la columna falta en el DB
        try:
            is_premium = bool(new_user["is_premium"])
        except (KeyError, TypeError):
            is_premium = False

        return TokenResponse(
            access_token=create_access_token(new_user["id"], new_user["username"]),
            refresh_token=create_refresh_token(new_user["id"]),
            user=_to_user_public(new_user),
        )

    except HTTPException:
        raise  # reenviar errores HTTP conocidos tal cual
    except Exception as exc:
        logger.error(f"Register error for '{body.username}': {exc}", exc_info=True)
        raise HTTPException(500, f"Error al registrar la cuenta: {str(exc)}")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    ip  = get_client_ip(request)
    val = body.email_or_username.strip()

    # ── Comprueba bloqueo por intentos fallidos ───────────────────────────────
    remaining = is_login_locked(ip, val)
    if remaining is not None:
        await log_audit(AuditAction.USER_LOGIN_LOCKED, ip_address=ip, success=False,
                        details={"identifier": val, "remaining_sec": int(remaining)})
        raise HTTPException(
            429,
            f"Cuenta bloqueada temporalmente por múltiples intentos fallidos. "
            f"Espera {lockout_remaining_str(remaining)} antes de intentarlo de nuevo."
        )

    user = await database.fetch_one(
        users.select().where(users.c.email == val.lower())
    )
    if not user:
        user = await database.fetch_one(
            users.select().where(
                func.lower(users.c.username) == val.lower()
            )
        )

    # Credenciales incorrectas o cuenta eliminada/desactivada
    if not user or not verify_password(body.password, user["password_hash"]):
        count = record_failed_login(ip, val)
        await log_audit(AuditAction.USER_LOGIN_FAIL, ip_address=ip, success=False,
                        details={"identifier": val, "attempt": count})
        raise HTTPException(401, "Credenciales incorrectas")

    if not user["is_active"]:
        await log_audit(AuditAction.USER_LOGIN_FAIL,
                        actor_user_id=user["id"], ip_address=ip, success=False,
                        details={"reason": "account_inactive"})
        raise HTTPException(403, "Cuenta desactivada")

    # Login exitoso — limpia intentos fallidos y registra auditoría
    clear_failed_login(ip, val)
    await log_audit(AuditAction.USER_LOGIN_SUCCESS, actor_user_id=user["id"],
                    ip_address=ip, success=True)

    return TokenResponse(
        access_token=create_access_token(user["id"], user["username"]),
        refresh_token=create_refresh_token(user["id"]),
        user=_to_user_public(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Refresh token inválido o expirado")
    user = await database.fetch_one(
        users.select().where(users.c.id == int(payload["sub"]))
    )
    if not user or not user["is_active"]:
        raise HTTPException(401, "Usuario no encontrado")

    return TokenResponse(
        access_token=create_access_token(user["id"], user["username"]),
        refresh_token=create_refresh_token(user["id"]),
        user=_to_user_public(user),
    )


@router.get("/me", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)):
    return _to_user_public(current_user)


@router.patch("/me", response_model=UserPublic)
async def update_me(body: UpdateProfileRequest, current_user=Depends(get_current_user)):
    """Actualiza el perfil del usuario autenticado.
    Requiere current_password si se cambia email o contraseña."""
    user_id = current_user["id"]
    updates: dict = {}

    # Verificar si se necesita contraseña actual
    changing_email = (
        body.email is not None and
        body.email.lower().strip() != current_user["email"]
    )
    changing_password = body.new_password is not None

    if changing_email or changing_password:
        if not body.current_password:
            raise HTTPException(
                400, "Se requiere la contraseña actual para cambiar email o contraseña"
            )
        if not verify_password(body.current_password, current_user["password_hash"]):
            raise HTTPException(401, "Contraseña actual incorrecta")

    # Username
    if body.username is not None:
        new_uname = body.username.strip()
        if new_uname.lower() != current_user["username"].lower():
            existing = await database.fetch_one(
                users.select().where(
                    func.lower(users.c.username) == new_uname.lower()
                ).where(users.c.id != user_id)
            )
            if existing:
                raise HTTPException(400, "El nombre de usuario ya está en uso")
        updates["username"] = new_uname

    # Email
    if changing_email:
        new_email = body.email.lower().strip()
        existing = await database.fetch_one(
            users.select().where(users.c.email == new_email).where(users.c.id != user_id)
        )
        if existing:
            raise HTTPException(400, "El email ya está registrado")
        updates["email"] = new_email

    # Bio
    if body.bio is not None:
        updates["bio"] = body.bio.strip()

    # Avatar
    if body.avatar is not None:
        updates["avatar"] = body.avatar

    # Password
    if changing_password:
        updates["password_hash"] = hash_password(body.new_password)

    if not updates:
        # Nada que cambiar — devuelve el usuario actual sin error
        return _to_user_public(current_user)

    await database.execute(
        users.update().where(users.c.id == user_id).values(**updates)
    )

    updated = await database.fetch_one(users.select().where(users.c.id == user_id))
    if not updated:
        raise HTTPException(500, "Error al actualizar el perfil")

    logger.info(f"Profile updated — user_id={user_id}, fields={list(updates.keys())}")

    # Auditoría granular según qué cambió
    if changing_password:
        await log_audit(AuditAction.USER_PASSWORD_CHANGE, actor_user_id=user_id, success=True)
    if changing_email:
        await log_audit(AuditAction.USER_EMAIL_CHANGE, actor_user_id=user_id, success=True,
                        details={"new_email": updates.get("email")})
    if set(updates.keys()) - {"password_hash", "email"}:
        await log_audit(AuditAction.USER_PROFILE_UPDATE, actor_user_id=user_id, success=True,
                        details={"fields": [k for k in updates if k not in ("password_hash", "email")]})

    return _to_user_public(updated)


@router.delete("/me", status_code=204)
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    current_user=Depends(get_current_user),
):
    """Soft-delete: desactiva la cuenta. Los datos se retienen 30 días para posible recuperación."""
    ip      = get_client_ip(request)
    user_id = current_user["id"]

    if not verify_password(body.password, current_user["password_hash"]):
        await log_audit(AuditAction.USER_DELETE, actor_user_id=user_id,
                        ip_address=ip, success=False,
                        details={"reason": "wrong_password"})
        raise HTTPException(400, "Contraseña incorrecta")

    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    await database.execute(
        users.update()
        .where(users.c.id == user_id)
        .values(
            is_active=False,
            deleted_at=now_naive,
        )
    )
    await log_audit(AuditAction.USER_DELETE, actor_user_id=user_id,
                    ip_address=ip, success=True,
                    details={"username": current_user["username"]})
    logger.info(
        f"Account soft-deleted — user_id={user_id}, username={current_user['username']}"
    )
    # 204 No Content


@router.post("/forgot-password", status_code=200)
async def forgot_password(body: ForgotPasswordRequest):
    user = await database.fetch_one(
        users.select().where(users.c.email == body.email.lower().strip())
    )
    # Siempre devuelve 200 para no revelar si el email existe
    if not user or not user["is_active"]:
        return {"message": "Si el email existe, recibirás un enlace de recuperación."}

    token = _create_reset_token(user["id"])
    reset_url = f"{settings.PUBLIC_URL}/auth/reset-form?token={token}"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0D0D0D;color:#fff;padding:40px;">
      <div style="max-width:480px;margin:0 auto;background:#1A1A1A;border-radius:16px;padding:32px;border:1px solid #2E2E2E;">
        <h2 style="color:#D4A843;margin-top:0;">One Piece TCG — Recuperación de contraseña</h2>
        <p>Hola <strong>{user['username']}</strong>,</p>
        <p>Recibimos una solicitud para restablecer tu contraseña. Haz clic en el botón para continuar:</p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{reset_url}" style="background:#D4A843;color:#0D0D0D;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:bold;font-size:16px;">
            Restablecer contraseña
          </a>
        </div>
        <p style="color:#888;font-size:12px;">Este enlace expira en {settings.RESET_TOKEN_EXPIRE_MINUTES} minutos.<br>
        Si no solicitaste esto, ignora este correo.</p>
      </div>
    </body></html>
    """

    try:
        await send_email(
            to=user["email"],
            subject="One Piece TCG — Restablecer contraseña",
            html_body=html,
        )
    except Exception:
        pass  # Falla silenciosamente si SMTP no está configurado

    return {"message": "Si el email existe, recibirás un enlace de recuperación."}


@router.get("/reset-form", response_class=HTMLResponse)
async def reset_form(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "reset":
            raise JWTError()
    except JWTError:
        return HTMLResponse(_error_page("El enlace es inválido o ha expirado."), status_code=400)

    return HTMLResponse(_reset_html(token))


@router.post("/reset-password", status_code=200)
async def reset_password(body: ResetPasswordRequest):
    try:
        payload = jwt.decode(body.token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "reset":
            raise JWTError()
    except JWTError:
        raise HTTPException(400, "El enlace es inválido o ha expirado.")

    user_id = int(payload["sub"])
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if not user or not user["is_active"]:
        raise HTTPException(400, "Usuario no encontrado")

    await database.execute(
        users.update()
        .where(users.c.id == user_id)
        .values(password_hash=hash_password(body.new_password))
    )
    return {"message": "Contraseña actualizada correctamente."}


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _reset_html(token: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Restablecer contraseña — One Piece TCG</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,sans-serif;background:#0D0D0D;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
  .card{{background:#1A1A1A;border:1px solid #2E2E2E;border-radius:16px;padding:32px;width:100%;max-width:420px}}
  h2{{color:#D4A843;margin-bottom:8px}}
  p{{color:#888;font-size:14px;margin-bottom:24px}}
  label{{display:block;color:#aaa;font-size:13px;margin-bottom:6px}}
  input{{width:100%;background:#222;border:1px solid #2E2E2E;border-radius:10px;padding:12px 14px;color:#fff;font-size:15px;outline:none;margin-bottom:16px}}
  input:focus{{border-color:#D4A843}}
  button{{width:100%;background:#D4A843;color:#0D0D0D;border:none;border-radius:10px;padding:14px;font-size:16px;font-weight:bold;cursor:pointer;margin-top:4px}}
  button:hover{{background:#c49a30}}
  .msg{{margin-top:16px;padding:12px;border-radius:8px;font-size:14px;text-align:center}}
  .ok{{background:#1a3a2a;color:#4caf81;border:1px solid #2a5a3a}}
  .err{{background:#2a1010;color:#ef9a9a;border:1px solid #5a1010}}
</style>
</head>
<body>
<div class="card">
  <h2>🔑 One Piece TCG</h2>
  <p>Ingresa tu nueva contraseña (mín. 8 caracteres, un número y un carácter especial).</p>
  <form id="form">
    <label>Nueva contraseña</label>
    <input type="password" id="pwd" placeholder="••••••••" required minlength="8">
    <label>Confirmar contraseña</label>
    <input type="password" id="pwd2" placeholder="••••••••" required minlength="8">
    <button type="submit">Restablecer contraseña</button>
  </form>
  <div id="msg"></div>
</div>
<script>
document.getElementById('form').addEventListener('submit', async e => {{
  e.preventDefault();
  const pwd = document.getElementById('pwd').value;
  const pwd2 = document.getElementById('pwd2').value;
  const msg = document.getElementById('msg');
  if (pwd !== pwd2) {{ msg.className='msg err'; msg.textContent='Las contraseñas no coinciden.'; return; }}
  const res = await fetch('/auth/reset-password', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{token: '{token}', new_password: pwd}})
  }});
  const data = await res.json();
  if (res.ok) {{
    msg.className='msg ok'; msg.textContent='✓ Contraseña actualizada. Ya puedes iniciar sesión en la app.';
    document.getElementById('form').style.display='none';
  }} else {{
    msg.className='msg err'; msg.textContent = data.detail || 'Error al restablecer.';
  }}
}});
</script>
</body></html>"""


def _error_page(message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Error</title>
<style>body{{font-family:Arial,sans-serif;background:#0D0D0D;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.card{{background:#1A1A1A;border:1px solid #5a1010;border-radius:16px;padding:32px;max-width:400px;text-align:center}}
h2{{color:#ef9a9a}}p{{color:#888;margin-top:8px}}</style>
</head><body><div class="card"><h2>Enlace inválido</h2><p>{message}</p></div></body></html>"""
