from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models import AgentMessages


async def get_agent_messages(
    session: AsyncSession,
    session_id: str,
    cursor: int | None,
    limit: int,
) -> list[AgentMessages]:
    stmt = select(AgentMessages).where(col(AgentMessages.session_id) == session_id)
    if cursor is not None:
        stmt = stmt.where(col(AgentMessages.id) < cursor)
    stmt = stmt.order_by(col(AgentMessages.id).desc()).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())
