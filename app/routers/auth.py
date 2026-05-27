import re
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

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
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    existing_email = await database.fetch_one(
        users.select().where(users.c.email == body.email.lower().strip())
    )
    if existing_email:
        raise HTTPException(400, "El email ya está registrado")

    # Comparación case-insensitive para username
    existing_user = await database.fetch_one(
        users.select().where(
            func.lower(users.c.username) == body.username.strip().lower()
        )
    )
    if existing_user:
        raise HTTPException(400, "El nombre de usuario ya está en uso")

    user_id = await database.execute(
        users.insert().values(
            username=body.username.strip(),
            email=body.email.lower().strip(),
            password_hash=hash_password(body.password),
            is_active=True,
            is_admin=False,
        )
    )
    new_user = await database.fetch_one(
        users.select().where(users.c.id == user_id)
    )
    return TokenResponse(
        access_token=create_access_token(new_user["id"], new_user["username"]),
        refresh_token=create_refresh_token(new_user["id"]),
        user=UserPublic(
            id=new_user["id"],
            username=new_user["username"],
            email=new_user["email"],
            created_at=new_user["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    val = body.email_or_username.strip()

    user = await database.fetch_one(
        users.select().where(users.c.email == val.lower())
    )
    if not user:
        user = await database.fetch_one(
            users.select().where(
                func.lower(users.c.username) == val.lower()
            )
        )
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Credenciales incorrectas")
    if not user["is_active"]:
        raise HTTPException(403, "Cuenta desactivada")

    return TokenResponse(
        access_token=create_access_token(user["id"], user["username"]),
        refresh_token=create_refresh_token(user["id"]),
        user=UserPublic(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
        ),
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
        user=UserPublic(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)):
    return UserPublic(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        created_at=current_user["created_at"],
    )


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
