from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

from ..database import database
from ..models import users
from ..core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)

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
        if len(v) > 50:
            raise ValueError("Máximo 50 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Mínimo 6 caracteres")
        return v


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


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


# ── get_current_user VA AQUÍ — antes de cualquier endpoint ───────────────────

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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    existing_email = await database.fetch_one(
        users.select().where(users.c.email == body.email.lower().strip())
    )
    if existing_email:
        raise HTTPException(400, "El email ya está registrado")

    existing_user = await database.fetch_one(
        users.select().where(users.c.username == body.username.strip())
    )
    if existing_user:
        raise HTTPException(400, "El nombre de usuario ya está en uso")

    user_id = await database.execute(
        users.insert().values(
            username=body.username.strip(),
            email=body.email.lower().strip(),
            password_hash=hash_password(body.password),
            is_active=True,
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
            users.select().where(users.c.username == val)
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