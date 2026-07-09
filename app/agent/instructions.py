from typing import Any

from agents import Agent, RunContextWrapper

from app.core.file import FileCachedLoader


class InstructionsLoader:
    def __init__(self, path: str) -> None:
        self._file_loader = FileCachedLoader(path=path)

    def load(
        self,
        _context: RunContextWrapper[Any],
        _agent: Agent[Any],
    ) -> str:
        return self._file_loader.load()
