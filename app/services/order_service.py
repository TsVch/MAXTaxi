from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.adapters.max_adapter import max_adapter
from app.models import Driver, Order, User
from app.schemas.messages import ButtonPayload, NormalizedMessage

logger = logging.getLogger("app.services.order")


@dataclass
class ServiceResponse:
    text: str
    buttons: list[ButtonPayload] | None = None


class TaxiBotService:
    def handle_message(self, db: Session, message: NormalizedMessage) -> ServiceResponse:
        if not message.user_id:
            return ServiceResponse(text="Unable to identify sender.")

        user = self._get_or_create_user(db, message.user_id)
        state = self._get_active_draft(db, user.id)
        text = message.text.strip()
        lowered = text.lower()

        if message.message_type == "button" and lowered.startswith("accept_order:"):
            order_id = int(lowered.split(":", 1)[1])
            return self._accept_order(db, message.user_id, order_id)

        if lowered == "start":
            return ServiceResponse(
                text="Welcome to MAX Taxi! Send 'order taxi' to create a ride request.",
                buttons=[ButtonPayload(text="Order taxi", payload="order taxi")],
            )

        if lowered == "order taxi":
            if state:
                state.status = "draft_from"
                state.from_address = ""
                state.to_address = ""
            else:
                state = Order(user_id=user.id, from_address="", to_address="", status="draft_from")
                db.add(state)
            db.commit()
            return ServiceResponse(text="Please enter your pickup address.")

        if state and state.status == "draft_from":
            state.from_address = text
            state.status = "draft_to"
            db.commit()
            return ServiceResponse(text="Got it. Now enter your destination address.")

        if state and state.status == "draft_to":
            state.to_address = text
            state.status = "new"
            db.commit()
            db.refresh(state)
            self._broadcast_order_to_drivers(db, state)
            return ServiceResponse(
                text=(
                    f"Your order is confirmed. From: {state.from_address}. "
                    f"To: {state.to_address}. Waiting for a driver."
                )
            )

        return ServiceResponse(
            text="Unknown command. Send 'start' to begin or 'order taxi' to request a ride."
        )

    def _get_or_create_user(self, db: Session, chat_id: str) -> User:
        user = db.scalar(select(User).where(User.chat_id == chat_id))
        if user:
            return user
        user = User(chat_id=chat_id)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def _get_active_draft(self, db: Session, user_id: int) -> Order | None:
        return db.scalar(
            select(Order)
            .where(Order.user_id == user_id, Order.status.in_(["draft_from", "draft_to"]))
            .order_by(Order.id.desc())
        )

    def _broadcast_order_to_drivers(self, db: Session, order: Order) -> None:
        drivers = db.scalars(select(Driver).where(Driver.is_available.is_(True))).all()
        for driver in drivers:
            max_adapter.send_buttons(
                driver.chat_id,
                (
                    f"New order #{order.id}: {order.from_address} → {order.to_address}. "
                    "Tap Accept to take it."
                ),
                [ButtonPayload(text="Accept", payload=f"accept_order:{order.id}")],
            )
        logger.info("Order broadcast to drivers", extra={"order_id": order.id, "drivers": len(drivers)})

    def _accept_order(self, db: Session, driver_chat_id: str, order_id: int) -> ServiceResponse:
        driver = db.scalar(select(Driver).where(Driver.chat_id == driver_chat_id))
        if not driver:
            return ServiceResponse(text="Driver profile not found.")

        claimed = db.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == "new", Order.driver_id.is_(None))
            .values(driver_id=driver.id, status="assigned")
        )
        if claimed.rowcount != 1:
            db.rollback()
            return ServiceResponse(text="Order already taken.")

        driver.is_available = False
        db.commit()

        order = db.scalar(select(Order).where(Order.id == order_id))
        if order is None:
            return ServiceResponse(text="Order not found after assignment.")

        max_adapter.send_message(order.user.chat_id, f"Driver {driver.name} is on the way for order #{order.id}.")

        other_drivers = db.scalars(select(Driver).where(Driver.id != driver.id)).all()
        for other_driver in other_drivers:
            max_adapter.send_message(other_driver.chat_id, f"Order #{order.id} already taken.")

        return ServiceResponse(text=f"You accepted order #{order.id}.")


bot_service = TaxiBotService()
