async def process_message(
    sender_id: str,
    message: str,
) -> str:

    text = message.lower().strip()

    if text in {"hi", "hello", "hey"}:
        return (
            "Hi! 👋 Welcome to Jingtorls AI Web Studio. "
            "How can we help you today?"
        )

    if "website" in text:
        return (
            "We build modern websites and web applications "
            "for businesses, researchers, and professionals."
        )

    if "ai" in text or "chatbot" in text:
        return (
            "We can build AI assistants, chatbots, and "
            "business automation systems."
        )

    return (
        "Thanks for contacting Jingtorls AI Web Studio! "
        "How can we help you?"
    )
