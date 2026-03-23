from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    orders: Mapped[list[Order]] = relationship(back_populates="user")


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    chat_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    orders: Mapped[list[Order]] = relationship(back_populates="driver")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    from_address: Mapped[str] = mapped_column(String(500))
    to_address: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)

    user: Mapped[User] = relationship(back_populates="orders")
    driver: Mapped[Driver | None] = relationship(back_populates="orders")
