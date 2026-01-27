from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum as SQLEnum, BigInteger, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class TradeDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"

class PaymentMethod(str, Enum):
    NONRES = "nonres"
    CASH = "cash"
    CASHLESS = "cashless"

class SessionStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"

class GroupStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")

class TradingSession(Base):
    __tablename__ = "trading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    currency_from = Column(String, nullable=False)
    currency_to = Column(String, nullable=False)
    volume = Column(Float, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    time_to_live_minutes = Column(Integer, default=60)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.CREATED)
    created_at = Column(DateTime, default=datetime.utcnow)
    target_tags = Column(JSON, default=list)

    orders = relationship("Order", back_populates="session")

    def is_expired(self) -> bool:
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds() > self.time_to_live_minutes * 60

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String, nullable=False)
    status = Column(SQLEnum(GroupStatus), default=GroupStatus.ACTIVE)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("Order", back_populates="group")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("trading_sessions.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    username = Column(String, nullable=True)
    side = Column(SQLEnum(TradeDirection), nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    message_id = Column(BigInteger, nullable=True)
    raw_message = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("TradingSession", back_populates="orders")
    group = relationship("Group", back_populates="orders")
    user = relationship("User", back_populates="orders")

    def is_valid(self) -> bool:
        return self.price > 0 and self.volume > 0

    def matches_session(self, session: TradingSession) -> bool:
        return (
            self.currency == session.currency_from and
            self.side != session.direction # Order side should be opposite to session direction for matching
        )
