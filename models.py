from sqlalchemy import BigInteger, create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, Session, Mapped, mapped_column, relationship, DeclarativeBase
import datetime
import json

Base = declarative_base()
metadata = MetaData()

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user_id
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(100), default="UTC")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    # Связи (для удобства на случай если предам crud запросы)
    portfolios: Mapped[list["Portfolio"]] = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
    "Subscription", back_populates="user", cascade="all, delete-orphan"
    )

class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint('user_id', 'ticker', name='uq_user_ticker'),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="portfolios")

class MarketAsset(Base):
    __tablename__ = "market_assets"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # удобнее сразу хранить
    
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Что мониторим
    indicator: Mapped[str] = mapped_column(String(30), default="price")  
    # "price", "rsi", "macd", "bbands_upper", "bbands_lower", "atr"
    
    condition: Mapped[str] = mapped_column(String(10))  # "above" / "below"
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Дополнительные параметры индикатора (опционально)
    # Например: {"period": 14} для RSI, {"window": 20, "k": 2} для Bollinger
    params: Mapped[str | None] = mapped_column(String(200), nullable=True)  # JSON-строка
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_one_shot: Mapped[bool] = mapped_column(Boolean, default=True)  # сработал → деактивировать
    
    last_triggered: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    # job_id в APScheduler (чтобы легко удалять)
    job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="alerts")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    sub_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "price" или "chart"
    
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")