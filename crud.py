from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, text
from models import User
from database import AsyncSessionLocal
import datetime, json

async def upsert_user(
    user_id: int,
    username: str | None,
    first_name: str | None,
    chat_id: int
):
    """Создаёт или обновляет пользователя"""
    query = text("""
        INSERT INTO users (id, username, first_name, chat_id, created_at)
        VALUES (:id, :username, :first_name, :chat_id, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            chat_id = excluded.chat_id
    """)
    
    async with AsyncSessionLocal() as session:
        await session.execute(query, {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "chat_id": chat_id
        })
        await session.commit()

async def update_timezone(user_id: int, timezone: str) -> None:
    """Обновляет таймзону пользователя"""
    query = text("""
        UPDATE users 
        SET timezone = :timezone 
        WHERE id = :user_id
    """)
    
    async with AsyncSessionLocal() as session:
        await session.execute(query, {"user_id": user_id, "timezone": timezone})
        await session.commit()

async def get_user_timezone(user_id: int) -> str:
    """Возвращает таймзону пользователя. По умолчанию UTC+0"""
    query = text("SELECT timezone FROM users WHERE id = :user_id")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"user_id": user_id})
        row = result.fetchone()
        tz = row[0] if row else None
        return tz if tz else "UTC+0"
    
# Пример получения chat_id (если понадобится)
async def get_chat_id(user_id: int) -> int | None:
    query = text("SELECT chat_id FROM users WHERE id = :user_id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"user_id": user_id})
        row = result.fetchone()
        return row[0] if row else None
    
async def add_to_portfolio(
    user_id: int,
    ticker: str,
    quantity: float,
    avg_buy_price: float
):
    """Добавить или обновить позицию в портфеле"""
    query = text("""
        INSERT INTO portfolios (user_id, ticker, quantity, avg_buy_price, created_at)
        VALUES (:user_id, :ticker, :quantity, :avg_buy_price, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, ticker) 
        DO UPDATE SET 
            avg_buy_price = (portfolios.quantity * portfolios.avg_buy_price + excluded.quantity * excluded.avg_buy_price) / (portfolios.quantity + excluded.quantity),
            quantity = portfolios.quantity + excluded.quantity,
            created_at = CURRENT_TIMESTAMP
    """)
    
    async with AsyncSessionLocal() as session:
        await session.execute(query, {
            "user_id": user_id,
            "ticker": ticker.upper(),
            "quantity": quantity,
            "avg_buy_price": avg_buy_price
        })
        await session.commit()


async def get_portfolio(user_id: int) -> list[dict]:
    """Получить весь портфель пользователя"""
    query = text("""
        SELECT ticker, quantity, avg_buy_price, created_at 
        FROM portfolios 
        WHERE user_id = :user_id
        ORDER BY ticker
    """)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]


async def get_portfolio_position(user_id: int, ticker: str) -> dict | None:
    """Получить одну позицию"""
    query = text("SELECT * FROM portfolios WHERE user_id = :user_id AND ticker = :ticker")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"user_id": user_id, "ticker": ticker.upper()})
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def remove_from_portfolio(user_id: int, ticker: str, quantity: float = None):
    """Удалить позицию полностью или частично"""
    if quantity is not None and quantity <= 0:
        raise ValueError("Quantity cannot be <= 0")
    
    if quantity is None:
        # Полное удаление
        query = text("DELETE FROM portfolios WHERE user_id = :user_id AND ticker = :ticker")
        params = {"user_id": user_id, "ticker": ticker.upper()}
    else:
        query = text("""
            UPDATE portfolios 
            SET quantity = quantity - :quantity 
            WHERE user_id = :user_id AND ticker = :ticker AND quantity >= :quantity AND quantity > 0
        """)
        params = {"user_id": user_id, "ticker": ticker.upper(), "quantity": quantity}
    
    async with AsyncSessionLocal() as session:
        await session.execute(query, params)
        await session.commit()








async def create_alert(
    user_id: int,
    chat_id: int,
    ticker: str,
    condition: str,
    target_value: float,
    indicator: str = "price",
    params: dict | None = None,
    is_one_shot: bool = True,
) -> int:
    """Создаёт алерт и возвращает его id"""
    query = text("""
        INSERT INTO alerts (
            user_id, chat_id, ticker, indicator, condition,
            target_value, params, is_one_shot, is_active, created_at
        )
        VALUES (
            :user_id, :chat_id, :ticker, :indicator, :condition,
            :target_value, :params, :is_one_shot, TRUE, :created_at
        )
        RETURNING id
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            query,
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "ticker": ticker.upper(),
                "indicator": indicator,
                "condition": condition,
                "target_value": target_value,
                "params": json.dumps(params) if params else None,
                "is_one_shot": is_one_shot,
                "created_at": datetime.datetime.utcnow(),
            },
        )
        await session.commit()
        return result.scalar_one()


async def get_user_alerts(user_id: int, only_active: bool = True) -> list[dict]:
    if only_active:
        query = text("""
            SELECT id, ticker, indicator, condition, target_value, params,
                   is_active, is_one_shot, job_id, created_at, last_triggered
            FROM alerts
            WHERE user_id = :user_id AND is_active = TRUE
            ORDER BY created_at DESC
        """)
    else:
        query = text("""
            SELECT id, ticker, indicator, condition, target_value, params,
                   is_active, is_one_shot, job_id, created_at, last_triggered
            FROM alerts
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "ticker": row.ticker,
                "indicator": row.indicator,
                "condition": row.condition,
                "target_value": row.target_value,
                "params": json.loads(row.params) if row.params else {},
                "is_active": row.is_active,
                "is_one_shot": row.is_one_shot,
                "job_id": row.job_id,
                "created_at": row.created_at,
                "last_triggered": row.last_triggered,
            }
            for row in rows
        ]


async def deactivate_alert(alert_id: int) -> None:
    query = text("UPDATE alerts SET is_active = FALSE WHERE id = :alert_id")

    async with AsyncSessionLocal() as session:
        await session.execute(query, {"alert_id": alert_id})
        await session.commit()


async def mark_alert_triggered(alert_id: int) -> None:
    query = text("""
        UPDATE alerts
        SET last_triggered = :now
        WHERE id = :alert_id
    """)

    async with AsyncSessionLocal() as session:
        await session.execute(
            query,
            {"alert_id": alert_id, "now": datetime.datetime.utcnow()},
        )
        await session.commit()


async def update_alert_job_id(alert_id: int, job_id: str) -> None:
    query = text("UPDATE alerts SET job_id = :job_id WHERE id = :alert_id")

    async with AsyncSessionLocal() as session:
        await session.execute(query, {"alert_id": alert_id, "job_id": job_id})
        await session.commit()


async def get_all_active_alerts() -> list[dict]:
    """Для загрузки при старте бота"""
    query = text("""
        SELECT id, user_id, chat_id, ticker, indicator, condition,
               target_value, params, is_active, is_one_shot, job_id,
               created_at, last_triggered
        FROM alerts
        WHERE is_active = TRUE
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "chat_id": row.chat_id,
                "ticker": row.ticker,
                "indicator": row.indicator,
                "condition": row.condition,
                "target_value": row.target_value,
                "params": json.loads(row.params) if row.params else {},
                "is_active": row.is_active,
                "is_one_shot": row.is_one_shot,
                "job_id": row.job_id,
                "created_at": row.created_at,
                "last_triggered": row.last_triggered,
            }
            for row in rows
        ]




#НОВЫЕ ИЗМЕНЕНИЯ

async def create_subscription(
    user_id: int,
    chat_id: int,
    ticker: str,
    sub_type: str,          # "price" или "chart"
    hour: int,
    minute: int,
) -> int:
    query = text("""
        INSERT INTO subscriptions (
            user_id, chat_id, ticker, sub_type, hour, minute, is_active, created_at
        )
        VALUES (
            :user_id, :chat_id, :ticker, :sub_type, :hour, :minute, TRUE, :created_at
        )
        RETURNING id
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {
            "user_id": user_id,
            "chat_id": chat_id,
            "ticker": ticker.upper(),
            "sub_type": sub_type,
            "hour": hour,
            "minute": minute,
            "created_at": datetime.datetime.utcnow(),
        })
        await session.commit()
        return result.scalar_one()


async def update_subscription_job_id(sub_id: int, job_id: str) -> None:
    query = text("UPDATE subscriptions SET job_id = :job_id WHERE id = :sub_id")
    async with AsyncSessionLocal() as session:
        await session.execute(query, {"sub_id": sub_id, "job_id": job_id})
        await session.commit()


async def get_all_active_subscriptions() -> list[dict]:
    query = text("""
        SELECT id, user_id, chat_id, ticker, sub_type, hour, minute, job_id
        FROM subscriptions
        WHERE is_active = TRUE
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]



async def get_user_subscriptions(user_id: int, only_active: bool = True) -> list[dict]:
    if only_active:
        query = text("""
            SELECT id, ticker, sub_type, hour, minute, job_id, created_at
            FROM subscriptions
            WHERE user_id = :user_id AND is_active = TRUE
            ORDER BY created_at DESC
        """)
    else:
        query = text("""
            SELECT id, ticker, sub_type, hour, minute, job_id, created_at, is_active
            FROM subscriptions
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]




async def deactivate_subscription(sub_id: int) -> None:
    query = text("UPDATE subscriptions SET is_active = FALSE WHERE id = :sub_id")
    async with AsyncSessionLocal() as session:
        await session.execute(query, {"sub_id": sub_id})
        await session.commit()