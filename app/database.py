import os
import databases
from sqlalchemy import create_engine

# Lee la URL desde variable de entorno (más seguro)
# Formato: postgresql://usuario:contraseña@host:5432/nombre_bd
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://op_user:op_password@localhost:5432/op_tcg"
)

database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL)
