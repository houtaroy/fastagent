from collections.abc import AsyncIterable

from agents import Runner
from fastapi import APIRouter, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.ag_ui.adapter import to_ag_ui_messages, to_ag_ui_stream
from app.agent.session import SQLAlchemySession
from app.api.deps import AgentDep, AsyncSessionDep
from app.core.db import async_engine
from app.crud import get_agent_messages
from app.models import AgentMessagesPublic, ChatCreate

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{id}/messages")
async def get_messages(
    id: str,
    session: AsyncSessionDep,
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> AgentMessagesPublic:
    rows = await get_agent_messages(
        session=session,
        session_id=id,
        cursor=cursor,
        limit=limit + 1,
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    page_rows.reverse()
    next_cursor = page_rows[0].id if has_more and page_rows else None
    messages = to_ag_ui_messages(page_rows)

    return AgentMessagesPublic(
        messages=messages,
        next_cursor=next_cursor,
        has_more=has_more,
    )


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

    async for event in to_ag_ui_stream(id, stream.stream_events()):
        raw_data = event.model_dump_json(by_alias=True, exclude_none=True)
        yield ServerSentEvent(raw_data=raw_data)
