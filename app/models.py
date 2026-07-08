from datetime import datetime

from ag_ui.core import Message
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Index, Integer, String, Text, text
from sqlmodel import Field, SQLModel


class AgentSessions(SQLModel, table=True):
    __tablename__ = "agent_sessions"

    session_id: str = Field(sa_column=Column(String, primary_key=True))
    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=False),
            server_default=text("CURRENT_TIMESTAMP"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=False),
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=text("CURRENT_TIMESTAMP"),
            nullable=False,
        )
    )


class AgentMessages(SQLModel, table=True):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("idx_agent_messages_session_time", "session_id", "created_at"),
        {"sqlite_autoincrement": True},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    session_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("agent_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    message_data: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=False),
            server_default=text("CURRENT_TIMESTAMP"),
            nullable=False,
        )
    )


class ChatCreate(SQLModel):
    content: str


class AgentMessagesPublic(SQLModel):
    messages: list[Message]
    next_cursor: int | None
    has_more: bool
