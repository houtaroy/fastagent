from collections.abc import AsyncIterable

from agents import RawResponsesStreamEvent, Runner
from fastapi import APIRouter, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy import select
from sqlmodel import col

from app.agent.session import SQLAlchemySession
from app.api.deps import AgentDep, AsyncSessionDep
from app.core.db import async_engine
from app.models import AgentMessages, AgentMessagesPublic, ChatCreate

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/{id}/chat", response_class=EventSourceResponse)
async def chat(
    id: str,
    body: ChatCreate,
    agent: AgentDep,
) -> AsyncIterable[ServerSentEvent]:

    stream = Runner.run_streamed(
        starting_agent=agent,
        input=body.content,
        session=SQLAlchemySession(session_id=id, engine=async_engine),
    )

    async for event in stream.stream_events():
        match event:
            case RawResponsesStreamEvent(data=data):
                yield ServerSentEvent(data=data)


@router.get("/{id}/messages")
async def get_messages(
    id: str,
    session: AsyncSessionDep,
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> AgentMessagesPublic:

    stmt = select(AgentMessages).where(col(AgentMessages.session_id) == id)
    if cursor is not None:
        stmt = stmt.where(col(AgentMessages.id) < cursor)
    stmt = stmt.order_by(col(AgentMessages.id).desc()).limit(limit + 1)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    messages = rows[:limit]
    messages.reverse()
    next_cursor = messages[0].id if has_more and messages else None

    return AgentMessagesPublic(
        messages=messages,
        next_cursor=next_cursor,
        has_more=has_more,
    )
