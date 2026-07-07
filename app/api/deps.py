from collections.abc import AsyncGenerator
from typing import Annotated, Any, cast

from agents import Agent
from fastapi import Depends, Request
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import async_session


async def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_async_openai(request: Request) -> AsyncOpenAI:
    return cast(AsyncOpenAI, request.app.state.async_openai)


AsyncOpenAIDep = Annotated[AsyncOpenAI, Depends(get_async_openai)]


async def get_agent(request: Request) -> Agent[Any]:
    return cast(Agent[Any], request.app.state.agent)


AgentDep = Annotated[Agent[Any], Depends(get_agent)]
