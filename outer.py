import aiohttp
import logging
import os
from config import settings
N8N_WEBHOOK_URL = settings.N8N_WEBHOOK_URL

logger = logging.getLogger(__name__)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")  # в .env

async def emit_event(event: str, **payload):
    """Отправляет событие в n8n. Ошибки не роняют бота."""
    if not N8N_WEBHOOK_URL:
        return

    data = {"event": event, **payload}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEBHOOK_URL,
                json=data,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status >= 400:
                    logger.warning("n8n webhook %s: %s", resp.status, await resp.text())
    except Exception as e:
        logger.warning("n8n webhook failed: %s", e)