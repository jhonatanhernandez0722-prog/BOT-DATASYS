from collections.abc import Mapping

from app.ai import get_ai_response
from app.bot import get_bot_response, get_relevant_context


async def get_assistant_response(
    message: str,
    documents: Mapping[str, str],
) -> tuple[str, str]:
    context = get_relevant_context(message, documents)
    ai_response = await get_ai_response(message, context)
    if ai_response is not None:
        return ai_response

    return get_bot_response(message, documents), "local"