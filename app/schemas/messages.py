from typing import Literal

from pydantic import BaseModel, Field


class NormalizedMessage(BaseModel):
    user_id: str
    text: str
    message_type: Literal["text", "button"] = "text"


class ButtonPayload(BaseModel):
    text: str
    payload: str


class OutgoingMessage(BaseModel):
    user_id: str
    text: str


class OutgoingButtonsMessage(OutgoingMessage):
    buttons: list[ButtonPayload] = Field(default_factory=list)


class MaxWebhookPayload(BaseModel):
    secret: str | None = None
    event_type: str = "message"
    sender: dict = Field(default_factory=dict)
    message: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)
