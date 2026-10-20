
import asyncio
from collections import deque

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.services.gemini import generate_reply


router = APIRouter(prefix="/webhook", tags=["Webhook"])

# In-memory duplicate protection for this running server.
# This cache resets when the application restarts.
MAX_SEEN_MESSAGES = 5000
seen_message_ids = set()
seen_message_order = deque()
message_lock = asyncio.Lock()


async def already_processed(message_id: str) -> bool:
    """Atomically check and record a Meta message ID."""
    async with message_lock:
        if message_id in seen_message_ids:
            return True

        seen_message_ids.add(message_id)
        seen_message_order.append(message_id)

        while len(seen_message_order) > MAX_SEEN_MESSAGES:
            oldest_id = seen_message_order.popleft()
            seen_message_ids.discard(oldest_id)

        return False


@router.get("")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(
        default=None, alias="hub.verify_token"
    ),
    hub_challenge: str | None = Query(
        default=None, alias="hub.challenge"
    ),
):
    if (
        hub_mode == "subscribe"
        and hub_verify_token == settings.meta_verify_token
    ):
        print("Meta webhook verification succeeded.")
        return PlainTextResponse(hub_challenge or "")

    print("Meta webhook verification failed.")
    return PlainTextResponse("Verification failed", status_code=403)


@router.post("")
async def receive_webhook(request: Request):
    data = await request.json()

    if data.get("object") != "page":
        return {"status": "ignored"}

    for entry in data.get("entry", []):
        page_id = entry.get("id")

        for event in entry.get("messaging", []):
            message = event.get("message", {})

            if message.get("is_echo"):
                continue

            sender_id = event.get("sender", {}).get("id")
            user_message = message.get("text")
            message_id = message.get("mid")

            if not sender_id or not user_message:
                continue

            # Skip duplicate deliveries of the same Meta message.
            if message_id:
                if await already_processed(message_id):
                    print(f"Ignoring duplicate message ID: {message_id}")
                    continue

            print(
                f"Processing message ID: {message_id or 'not provided'}"
            )

            # Retry temporary Gemini failures up to three times.
            reply_text = None

            for attempt in range(1, 4):
                try:
                    reply_text = await generate_reply(
                        user_message,
                        conversation_id=sender_id,
                    )
                    print("Gemini generated a reply.")
                    break
                except Exception as exc:
                    print(
                        f"Gemini attempt {attempt}/3 failed: "
                        f"{type(exc).__name__}"
                    )

                    if attempt < 3:
                        await asyncio.sleep(attempt)

            if not reply_text:
                reply_text = (
                    "Sorry, I'm having trouble answering right now. "
                    "Please try again shortly."
                )

            page_token = settings.meta_page_access_token
            if not page_token:
                print("ERROR: META_PAGE_ACCESS_TOKEN is missing.")
                continue

            url = (
                f"https://graph.facebook.com/v26.0/"
                f"{page_id}/messages"
            )

            payload = {
                "recipient": {"id": sender_id},
                "messaging_type": "RESPONSE",
                "message": {"text": reply_text},
            }

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {page_token}"
                        },
                    )

                if response.is_success:
                    print("Messenger reply sent successfully.")
                else:
                    print(
                        "Messenger API returned HTTP",
                        response.status_code,
                    )
                    print("API response:", response.text[:1000])

            except httpx.HTTPError as exc:
                print(
                    "Messenger request failed:",
                    type(exc).__name__,
                )

    return {"status": "received"}
