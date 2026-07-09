from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agents import Agent, ModelSettings, set_default_openai_client, set_tracing_disabled
from fastapi import FastAPI
from openai import AsyncOpenAI
from openai.types import Reasoning

from app.agent.instructions import InstructionsLoader
from app.agent.tools import get_weather
from app.api.main import api_router
from app.core.config import settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.settings = settings

    await init_db()

    async_openai = AsyncOpenAI(
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
    )
    app.state.async_openai = async_openai

    set_default_openai_client(async_openai, use_for_tracing=False)
    set_tracing_disabled(not settings.OPENAI_TRACING)
    instructions_loader = InstructionsLoader(path=settings.AGENT_INSTRUCTIONS_FILE)
    agent = Agent(
        name=settings.AGENT_NAME,
        model=settings.AGENT_MODEL,
        model_settings=ModelSettings(
            reasoning=Reasoning(effort=settings.AGENT_MODEL_REASONING)
        ),
        instructions=instructions_loader.load,
        tools=[get_weather],
    )
    app.state.agent = agent

    yield

    await async_openai.close()


app = FastAPI(title="FastAgent", lifespan=lifespan)

app.include_router(api_router)
