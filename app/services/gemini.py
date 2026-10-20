
from collections import OrderedDict
import asyncio

from google import genai
from google.genai import types

from app.core.config import settings


client = (
    genai.Client(api_key=settings.gemini_api_key)
    if settings.gemini_api_key
    else None
)

SYSTEM_INSTRUCTION = """
You are a helpful, friendly AI assistant communicating through Facebook
Messenger.

Your primary job is to answer the user's actual question helpfully.
You can discuss general topics, including science, physics, technology,
education, programming, quantum computing, and everyday questions.

Conversation rules:
- Answer the latest question directly.
- Do not greet the user again in every response.
- Use earlier messages to understand follow-up questions.
- Explain difficult topics in clear, approachable language.
- Ask a follow-up question only when it would genuinely help.
- Keep replies concise enough for Messenger, unless more detail is useful.
- Match the user's language and level of understanding.
- Do not claim to have performed actions you have not performed.

Business rules:
- You can help with questions about VZX Labs when the user asks about it.
- Do not force unrelated questions back to VZX Labs.
- Do not invent VZX Labs services, prices, policies, contact details,
  or business hours.
- If asked for an unknown business-specific fact, explain that a team
  member should confirm it.
"""

# In-memory conversation history: it resets when the server restarts.
# Store at most 12 messages per user and 500 users.
MAX_HISTORY_MESSAGES = 12
MAX_CONVERSATIONS = 500

conversation_histories: OrderedDict[str, list[types.Content]] = (
    OrderedDict()
)
conversation_locks: dict[str, asyncio.Lock] = {}
state_lock = asyncio.Lock()


async def get_user_lock(user_id: str) -> asyncio.Lock:
    async with state_lock:
        lock = conversation_locks.get(user_id)

        if lock is None:
            lock = asyncio.Lock()
            conversation_locks[user_id] = lock

        return lock


async def generate_reply(user_message: str, conversation_id: str) -> str:
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is missing from .env.")

    # Serialize requests for each user so their conversation stays ordered.
    user_lock = await get_user_lock(conversation_id)

    async with user_lock:
        history = conversation_histories.get(conversation_id, [])

        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=[
                *history,
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=400,
            ),
        )

        answer = (response.text or "").strip()

        if not answer:
            raise RuntimeError("Gemini returned an empty response.")

        if len(answer) > 1800:
            answer = answer[:1797].rstrip() + "..."

        # Save only successful exchanges, not failed API requests.
        updated_history = [
            *history,
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=answer)],
            ),
        ]

        conversation_histories[conversation_id] = (
            updated_history[-MAX_HISTORY_MESSAGES:]
        )
        conversation_histories.move_to_end(conversation_id)

        # Bound memory use if many different users message the Page.
        while len(conversation_histories) > MAX_CONVERSATIONS:
            oldest_user_id, _ = conversation_histories.popitem(last=False)
            conversation_locks.pop(oldest_user_id, None)

        return answer
