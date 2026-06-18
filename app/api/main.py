from fastapi import FastAPI

from app.api.routes.conversations import router as conversations_router
from app.core.database import Base, engine

# Crear las tablas de base de datos si no existen
# Nota: En producción con PostgreSQL, se pueden gestionar externamente o vía Alembic,
# pero esto asegura el funcionamiento inmediato para desarrollo local.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Normativa Agentica",
    description="Servicio FastAPI para la gestión de normativa agentica",
    version="0.1.0",
)

# Incluir el router con el prefijo /api
app.include_router(conversations_router, prefix="/api")


@app.get("/", tags=["Root"])
async def read_root() -> dict[str, str]:
    """
    Endpoint base que retorna un mensaje de saludo "Hola Mundo".
    """
    return {"message": "Hola Mundo"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)

