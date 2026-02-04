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

class GroupStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TradingSession(Base):
    __tablename__ = "trading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    currency_from = Column(String, nullable=False)
    currency_to = Column(String, nullable=False)
    volume = Column(String, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    time_to_live_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
    target_tags = Column(JSON, default=list)
    
    # Custom broadcast fields
    is_custom_broadcast = Column(Boolean, default=False)
    custom_message = Column(String, nullable=True)

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

