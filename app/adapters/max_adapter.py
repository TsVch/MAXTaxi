import logging
from threading import Lock

from app.schemas.messages import ButtonPayload, MaxWebhookPayload, NormalizedMessage

logger = logging.getLogger("app.adapters.max")

_SENT_MESSAGES: list[dict] = []
_MESSAGES_LOCK = Lock()


class MaxAdapter:
    """Abstraction layer for MAX messenger integration."""

    def parse_webhook(self, payload: MaxWebhookPayload) -> NormalizedMessage:
        sender = payload.sender or {}
        message = payload.message or {}
        callback_payload = payload.payload or {}

        user_id = str(sender.get("id") or callback_payload.get("user_id") or "")
        message_type = "button" if callback_payload.get("action") else "text"
        text = (
            callback_payload.get("action")
            or message.get("text")
            or callback_payload.get("text")
            or ""
        )

        normalized = NormalizedMessage(user_id=user_id, text=text.strip(), message_type=message_type)
        logger.info("Incoming MAX message normalized", extra={"payload": normalized.model_dump()})
        return normalized

    def send_message(self, user_id: str, text: str) -> dict:
        message = {"type": "text", "user_id": user_id, "text": text}
        self._store(message)
        logger.info("Outgoing MAX text message", extra={"payload": message})
        return message

    def send_buttons(self, user_id: str, text: str, buttons: list[ButtonPayload | dict]) -> dict:
        normalized_buttons = [button.model_dump() if isinstance(button, ButtonPayload) else button for button in buttons]
        message = {"type": "buttons", "user_id": user_id, "text": text, "buttons": normalized_buttons}
        self._store(message)
        logger.info("Outgoing MAX button message", extra={"payload": message})
        return message

    def list_sent_messages(self) -> list[dict]:
        with _MESSAGES_LOCK:
            return list(_SENT_MESSAGES)

    def reset_mock_outbox(self) -> None:
        with _MESSAGES_LOCK:
            _SENT_MESSAGES.clear()

    def _store(self, message: dict) -> None:
        with _MESSAGES_LOCK:
            _SENT_MESSAGES.append(message)


max_adapter = MaxAdapter()
