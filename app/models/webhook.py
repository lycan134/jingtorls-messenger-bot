from typing import Any

from pydantic import BaseModel


class WebhookEvent(BaseModel):
    object: str | None = None
    entry: list[Any] = []