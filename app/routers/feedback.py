from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import database
from ..models import feedback as feedback_table
from ..core.security import decode_token
from ..models import users

router = APIRouter(prefix="/feedback", tags=["feedback"])
_bearer = HTTPBearer(auto_error=False)


class FeedbackCreate(BaseModel):
    message: str
    type: str = "feedback"  # feedback | bug | suggestion


class FeedbackResponse(BaseModel):
    id: int
    type: str
    message: str
    created_at: datetime


async def _optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    user = await database.fetch_one(
        users.select().where(users.c.id == int(payload["sub"]))
    )
    return user if user and user["is_active"] else None


@router.post("", response_model=FeedbackResponse, status_code=201)
async def create_feedback(
    body: FeedbackCreate,
    current_user=Depends(_optional_user),
):
    msg = body.message.strip()
    if not msg:
        raise HTTPException(400, "El mensaje no puede estar vacío")
    if len(msg) > 500:
        raise HTTPException(400, "El mensaje no puede superar los 500 caracteres")

    valid_types = {"feedback", "bug", "suggestion"}
    msg_type = body.type if body.type in valid_types else "feedback"

    row_id = await database.execute(
        feedback_table.insert().values(
            user_id=current_user["id"] if current_user else None,
            type=msg_type,
            message=msg,
            is_read=False,
        )
    )
    row = await database.fetch_one(
        feedback_table.select().where(feedback_table.c.id == row_id)
    )
    return FeedbackResponse(
        id=row["id"],
        type=row["type"],
        message=row["message"],
        created_at=row["created_at"],
    )
