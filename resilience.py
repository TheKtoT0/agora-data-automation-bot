import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar
from cachetools import TTLCache
from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ====================== КЭШ ======================
# Хранит результаты get_price на 45 секунд
price_cache: TTLCache = TTLCache(maxsize=300, ttl=45)


def clear_price_cache():
    """На всякий случай, если понадобится сбросить"""
    price_cache.clear()


# ====================== РЕТРАИ ======================
async def retry_async(
    func: Callable[..., Any],
    *args,
    attempts: int = 3,
    delay: float = 1.2,
    backoff: float = 1.8,
    exceptions: tuple = (Exception,),
    **kwargs,
) -> Any:
    """
    Простой асинхронный retry с экспоненциальной задержкой.
    """
    last_exc = None
    current_delay = delay

    for attempt in range(1, attempts + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exc = e
            if attempt == attempts:
                break
            logger.warning(
                f"[retry] {func.__name__} failed (attempt {attempt}/{attempts}): {e}. "
                f"Retrying in {current_delay:.1f}s..."
            )
            await asyncio.sleep(current_delay)
            current_delay *= backoff

    raise last_exc


# ====================== БЕЗОПАСНЫЕ ОБЁРТКИ ======================

async def safe_get_price(ticker: str, use_cache: bool = True):
    """
    Безопасная версия get_price с кэшем и ретраями.
    Возвращает dict или None при полном провале.
    """
    from servicesnstuff import get_price  # локальный импорт, чтобы избежать циклов

    ticker = ticker.upper().strip()

    # 1. Кэш
    if use_cache and ticker in price_cache:
        return price_cache[ticker]

    # 2. Ретраи
    try:
        data = await retry_async(
            get_price,
            ticker,
            attempts=3,
            delay=1.0,
            backoff=1.7,
        )
        if data is not None:
            price_cache[ticker] = data
        return data
    except Exception as e:
        logger.error(f"[safe_get_price] Все попытки провалились для {ticker}: {e}")
        return None


async def safe_fetch_current_price(ticker: str) -> float | None:
    """
    Безопасная обёртка над fetch_current_price (синхронная функция).
    """
    from servicesnstuff import fetch_current_price

    ticker = ticker.upper().strip()

    # Можно тоже кэшировать, если хочешь
    cache_key = f"price_only:{ticker}"
    if cache_key in price_cache:
        return price_cache[cache_key]

    try:
        # так как fetch_current_price синхронный — запускаем в thread
        price = await asyncio.to_thread(fetch_current_price, ticker)
        if price is not None:
            price_cache[cache_key] = price
        return price
    except Exception as e:
        logger.error(f"[safe_fetch_current_price] Ошибка для {ticker}: {e}")
        return None


def graceful(fallback_message: str = "⚠️ Временно не удалось получить данные. Попробуй позже."):
    """
    Декоратор для хэндлеров.
    Если внутри возникла ошибка — отправляет понятное сообщение вместо traceback.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            try:
                return await func(message, *args, **kwargs)
            except Exception as e:
                logger.exception(f"Ошибка в {func.__name__}: {e}")
                try:
                    await message.answer(fallback_message)
                except Exception:
                    pass
        return wrapper
    return decorator