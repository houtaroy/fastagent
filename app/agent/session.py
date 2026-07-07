import json

from agents.extensions.memory import SQLAlchemySession as OpenAISQLAlchemySession
from agents.items import TResponseInputItem


class SQLAlchemySession(OpenAISQLAlchemySession):
    async def _serialize_item(self, item: TResponseInputItem) -> str:
        return json.dumps(item, separators=(",", ":"), ensure_ascii=False)
