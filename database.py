from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from datetime import datetime
from config import settings
import os
import logging

logger = logging.getLogger(__name__)

# Base = declarative_base()
# metadata = MetaData()

# class User(Base):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True)
#     username = Column(String(64), nullable=True)
#     timezone = Column(String(32), default="UTC")
#     created_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# class Portfeli():
#     __tablename__ = "user_positions"

#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     ticker = Column(Float, nullable=False)
#     quantity = Column(Float, nullable=False)
#     avg_buy_price = Column(Float)
#     added_at = Column(DateTime, default=datetime.utcnow)

# class BasicAssets():
#     __tablename__ = "market_assets"

#     ticker = Column(String(20), primary_key=True)
#     name = Column(String(128))
#     asset_type = Column(String(20))
#     sector = Column(String(64))
#     last_price = Column(Float)
#     last_updated = Column(DateTime)
#     is_popular = Column(Boolean, default=False)
    
# class AlertSystem():
#     __tablename__ = "user_alerts"

#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     ticker = Column(String(20))
#     condition = Column(String(20))
#     target_value = Column(Float)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime, default=datetime.utcnow)

# engine = create_engine("sqlite:///agora_bdshka_rabochee.db", echo=True)
# metadata.create_all(engine)

# with Session(engine) as session:
#     users = session.query(User).all()  # Получить все записи
#     for user in users:
#         print(user.id, user.username)

# ^^^^^^^^^ СТАРЫЕ МОДЕЛИ ГОВНОКОД СМЕРТЕЛЬНЫЙ ФАЙЛ




from models import Base

DATABASE_URL = settings.DATABASE_URL   # создаст папку data/ автоматически

engine = create_async_engine(DATABASE_URL, echo=False)  # echo на True для отладки
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db(drop_existing: bool = False) -> None:
    """Инициализация БД. При drop_existing=True — полностью пересоздаёт базу"""
    if drop_existing and os.path.exists("agora_bdshka_RABOCHAYA.db"):
        os.remove("agora_bdshka_RABOCHAYA.db")
        logger.info("Old database deleted")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database initialized")