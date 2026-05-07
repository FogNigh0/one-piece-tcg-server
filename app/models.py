import sqlalchemy
from sqlalchemy import MetaData

metadata = MetaData()

# Tabla principal: todas las cartas del juego
cards = sqlalchemy.Table(
    "cards",
    metadata,
    sqlalchemy.Column("id",         sqlalchemy.String, primary_key=True),   # OP14-079
    sqlalchemy.Column("name",       sqlalchemy.String, nullable=False),
    sqlalchemy.Column("set_code",   sqlalchemy.String, nullable=False),      # OP14
    sqlalchemy.Column("number",     sqlalchemy.String, nullable=False),      # 079
    sqlalchemy.Column("card_type",  sqlalchemy.String),                      # CHARACTER, LEADER, EVENT, STAGE
    sqlalchemy.Column("color",      sqlalchemy.String),                      # Red, Blue, etc.
    sqlalchemy.Column("cost",       sqlalchemy.Integer),
    sqlalchemy.Column("power",      sqlalchemy.Integer),
    sqlalchemy.Column("counter",    sqlalchemy.Integer),
    sqlalchemy.Column("attribute",  sqlalchemy.String),                      # Slash, Strike, etc.
    sqlalchemy.Column("faction",    sqlalchemy.String),                      # Straw Hat Crew, etc.
    sqlalchemy.Column("effect",     sqlalchemy.Text),
    sqlalchemy.Column("trigger",    sqlalchemy.Text),
    sqlalchemy.Column("rarity",     sqlalchemy.String),                      # C, UC, R, SR, SEC, L
    sqlalchemy.Column("image_url",  sqlalchemy.String),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
)

# Tabla de mazos guardados por el usuario
decks = sqlalchemy.Table(
    "decks",
    metadata,
    sqlalchemy.Column("id",         sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("name",       sqlalchemy.String, nullable=False),
    sqlalchemy.Column("cards_text", sqlalchemy.Text, nullable=False),  # "3xOP05-082 1xOP11-097 ..."
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()),
)

# ── Usuarios ──────────────────────────────────────────────────────────────────
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id",            sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("username",      sqlalchemy.String(50), unique=True, nullable=False, index=True),
    sqlalchemy.Column("email",         sqlalchemy.String(255), unique=True, nullable=False, index=True),
    sqlalchemy.Column("password_hash", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, nullable=False, default=True, server_default="true"),
    sqlalchemy.Column("created_at",    sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
)

# ── Carpetas de usuario ───────────────────────────────────────────────────────
user_folders = sqlalchemy.Table(
    "user_folders",
    metadata,
    sqlalchemy.Column("id",          sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("user_id",     sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    sqlalchemy.Column("name",        sqlalchemy.String(120), nullable=False),
    sqlalchemy.Column("is_public",   sqlalchemy.Boolean, default=False, server_default="0", nullable=False),
    sqlalchemy.Column("share_token", sqlalchemy.String(36), unique=True, nullable=True, index=True),
    sqlalchemy.Column("created_at",  sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
)

# ── Cartas dentro de carpetas de usuario ──────────────────────────────────────
user_folder_cards = sqlalchemy.Table(
    "user_folder_cards",
    metadata,
    sqlalchemy.Column("id",            sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("folder_id",     sqlalchemy.Integer, sqlalchemy.ForeignKey("user_folders.id", ondelete="CASCADE"), nullable=False, index=True),
    sqlalchemy.Column("card_set_code", sqlalchemy.String(30), nullable=False),  # ej: OP14-091
    sqlalchemy.Column("quantity",      sqlalchemy.Integer, default=1, nullable=False),
)

user_collection = sqlalchemy.Table(
    "user_collection",
    metadata,
    sqlalchemy.Column("id",            sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("user_id",       sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    sqlalchemy.Column("card_set_code", sqlalchemy.String(50), nullable=False),
    sqlalchemy.Column("quantity",      sqlalchemy.Integer, default=1, nullable=False),
    sqlalchemy.Column("updated_at",    sqlalchemy.DateTime, server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()),
)