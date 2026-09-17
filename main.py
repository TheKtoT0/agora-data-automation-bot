import asyncio
import yfinance as yf
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
import os
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import settings
from handlers import *
from database import *
from jobs import *
from scheduler import *


import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # в консоль
            RotatingFileHandler(
                "bot.log",
                maxBytes=5_000_000,   # 5 MB
                backupCount=3,
                encoding="utf-8"
            )
        ]
    )
    
    # шобы меньше шумели сторонние библиотеки
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("yfinance").setLevel(logging.WARNING)


bot = Bot(token=settings.BOT_TOKEN)

async def on_start():
    start_scheduler()

async def on_shutdown():
    shutdown_scheduler()

async def on_start_OLD():
    start_scheduler()
    
    # Восстанавливаем все активные алерты
    active_alerts = await get_all_active_alerts()
    for alert in active_alerts:
        await add_ind_alert_job(
            bot=bot,
            chat_id=alert["chat_id"],
            ticker=alert["ticker"],
            indicator=alert["indicator"],
            target_value=alert["target_value"],
            condition=alert["condition"],
            job_id=alert["job_id"] or f"alert_{alert['id']}",
            alert_id=alert["id"]
        )
    logger.info(f"Восстановлено {len(active_alerts)} алертов")

async def on_start():
    start_scheduler()

    # Восстанавливаем алерты (уже есть)
    active_alerts = await get_all_active_alerts()
    for alert in active_alerts:
        job_id = alert["job_id"] or f"alert_{alert['id']}"
        await add_ind_alert_job(
            bot=bot,
            chat_id=alert["chat_id"],
            ticker=alert["ticker"],
            indicator=alert["indicator"],
            target_value=alert["target_value"],
            condition=alert["condition"],
            job_id=job_id,
            alert_id=str(alert["id"]),          # в add_ind_alert_job ожидается str
        )
        # на всякий случай обновляем job_id в БД, если его не было
        if not alert["job_id"]:
            await update_alert_job_id(alert["id"], job_id)

    # Восстанавливаем подписки
    active_subs = await get_all_active_subscriptions()
    for sub in active_subs:
        if sub["sub_type"] == "price":
            await add_daily_price_job(
                bot=bot,
                chat_id=sub["chat_id"],
                ticker=sub["ticker"],
                hour=sub["hour"],
                minute=sub["minute"],
                job_id=sub["job_id"] or f"daily_price_{sub['id']}"
            )
        elif sub["sub_type"] == "chart":
            await add_daily_chart_job(
                bot=bot,
                chat_id=sub["chat_id"],
                ticker=sub["ticker"],
                hour=sub["hour"],
                minute=sub["minute"],
                job_id=sub["job_id"] or f"daily_chart_{sub['id']}"
            )
        elif sub["sub_type"] == "report":
            await add_daily_report_ticker_job(
                bot=bot,
                chat_id=sub["chat_id"],
                ticker=sub["ticker"],
                hour=sub["hour"],
                minute=sub["minute"],
                job_id=sub["job_id"] or f"daily_report_{sub['id']}"
            )

    logger.info(f"Восстановлено {len(active_alerts)} алертов и {len(active_subs)} подписок")

async def main():
    setup_logging()
    await init_db(drop_existing=False)
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    dp.startup.register(on_start)
    dp.shutdown.register(on_shutdown)

    dp.include_router(rtr)

    logger.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())