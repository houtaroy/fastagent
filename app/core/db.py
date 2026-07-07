import json

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings

async_engine = create_async_engine(
    settings.DATABASE_URI,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
