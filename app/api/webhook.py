from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.max_adapter import max_adapter
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Driver, Order
from app.schemas.messages import MaxWebhookPayload
from app.schemas.orders import OrderRead
from app.services.order_service import bot_service

router = APIRouter(prefix="/webhook", tags=["webhooks"])
mock_router = APIRouter(prefix="/mock", tags=["mock"])


@router.post("/max")
def max_webhook(
    payload: MaxWebhookPayload,
    db: Session = Depends(get_db),
    x_max_secret: str | None = Header(default=None),
):
    settings = get_settings()
    provided_secret = x_max_secret or payload.secret
    if settings.max_webhook_secret and provided_secret != settings.max_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid MAX webhook secret")

    normalized = max_adapter.parse_webhook(payload)
    response = bot_service.handle_message(db, normalized)
    if response.buttons:
        max_adapter.send_buttons(normalized.user_id, response.text, response.buttons)
    else:
        max_adapter.send_message(normalized.user_id, response.text)
    return {"status": "ok", "normalized": normalized.model_dump(), "response": response.text}


@mock_router.get("/outbox")
def get_mock_outbox():
    return {"messages": max_adapter.list_sent_messages()}


@mock_router.delete("/outbox")
def reset_mock_outbox():
    max_adapter.reset_mock_outbox()
    return {"status": "cleared"}


@mock_router.post("/seed-drivers")
def seed_drivers(db: Session = Depends(get_db)):
    drivers = [
        ("Alice", "driver_alice"),
        ("Bob", "driver_bob"),
        ("Charlie", "driver_charlie"),
    ]
    created = []
    for name, chat_id in drivers:
        existing = db.scalar(select(Driver).where(Driver.chat_id == chat_id))
        if existing:
            created.append(existing.chat_id)
            continue
        driver = Driver(name=name, chat_id=chat_id, is_available=True)
        db.add(driver)
        created.append(chat_id)
    db.commit()
    return {"seeded": created}


@mock_router.get("/orders", response_model=list[OrderRead])
def list_orders(db: Session = Depends(get_db)):
    return db.scalars(select(Order).order_by(Order.id.desc())).all()
