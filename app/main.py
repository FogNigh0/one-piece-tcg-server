from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import database, engine
from .models import metadata
from .routers import cards, decks

app = FastAPI(title="One Piece TCG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(decks.router)

@app.on_event("startup")
async def startup():
    metadata.create_all(engine)
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/")
async def root():
    return {"status": "ok", "message": "One Piece TCG API funcionando"}
