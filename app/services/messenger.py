async def send_message(
    recipient_id: str,
    message: str,
):
    """
    Sends a message to a Messenger user.

    Meta API integration will be added here.
    """

    print("Sending Messenger message:")
    print(f"Recipient: {recipient_id}")
    print(f"Message: {message}")

    return {
        "status": "simulated",
        "recipient_id": recipient_id,
        "message": message,
    }
