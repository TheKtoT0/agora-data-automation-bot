import asyncio
import logging
from datetime import datetime as dt
from aiogram import Bot, types
from servicesnstuff import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from indicators import *
# from scheduler import * <------ НЕ РАСКОММЕНТИРУЙ, иначе цикличный импорт
from crud import *
from outer import emit_event

logger = logging.getLogger(__name__)



async def send_daily_price(
    bot: Bot,
    chat_id: int,
    ticker: str,
    user_timezone: str | None = None
):
    """Ежедневная отправка цены актива"""
    try:

        tz_info = parse_utc_offset(user_timezone)
        if tz_info is None:
            tz_info = timezone.utc  # fallback

        now_local = dt.now(tz_info)

        data = await get_price(ticker)  # функция из servicesnstuff
        
        text = (
            f"📅 <b>Daily report</b>\n"
            f"🕒 {dt.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🎯 Asset: <b>{ticker}</b>\n"
            f"💰 Price: ${data.get('price', 0):.2f}\n"
            f"📈 Change: {data.get('change', 0):+.2f}%\n"
        )
        
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML"
        )
        
        logger.info(f"Sending daily price {ticker} to user {chat_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке цены {ticker} для {chat_id}: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error: {str(e)}"
            )
        except:
            pass

async def send_daily_chart(
        bot: Bot,
        chat_id: int,
        ticker: str,
        user_timezone: str | None = None
):
    """Ежедневная отправка графика цены актива за день"""
    try:

        tz_info = parse_utc_offset(user_timezone)
        if tz_info is None:
            tz_info = timezone.utc  # fallback
        
        data = await get_pricechart_daily(ticker)

        text = (
            f"📅 <b>Daily report</b>\n"
            f"🕒 {dt.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🎯 Asset: <b>{ticker}</b>\n"
            f"💰 Chart:"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML"
        )

        await bot.send_photo(
            chat_id=chat_id,
            photo=types.BufferedInputFile(
            file=data.getvalue(),          # именно .getvalue() → bytes (файлы все дела)
            filename=f"{ticker}_1d.png"
            ),
            caption="table"
        )

        logger.info(f"Sent a daily pricechart for {ticker} to user {chat_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке графика {ticker} для {chat_id}: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error: {str(e)}"
            )
        except:
            pass













async def send_daily_report_ticker(
        bot: Bot,
        chat_id: int,
        ticker: str,
        user_timezone: str | None
        # report_type: str | None = None
):
    """Ежедневная отправка отчёта с базовой информацией по тикеру"""
    try:
    
        tz_info = parse_utc_offset(user_timezone)
        if tz_info is None:
            tz_info = timezone.utc  # fallback

        filename = f"{ticker}_report.pdf"
        pdf_bytes = await asyncio.to_thread(generate_report_no_save, ticker)
        file_bytes = types.BufferedInputFile(file=pdf_bytes,
                                               filename=filename)

          # функция из servicesnstuff

        await bot.send_document(
            chat_id=chat_id,
            document=file_bytes
        )

        logger.info(f"Sending a daily report for {ticker} to user {chat_id}")

    except Exception as e:
        logger.error(f"An error occured during an attempt to send report {ticker} for {chat_id}: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error: {str(e)}"
            )
        except:
            pass







# АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ АЛЕРТЫ

# async def send_alert_price_stariy(
#         bot: Bot,
#         chat_id: int,
#         ticker: str,     
#         condition_text: str, 
# ):
#     """Отправка предупреждения при срабатывании условия алерта"""
#     text = (
#         f"ALERT!"
#         f"Condition {condition_text} has been triggered."
#     )

#     await bot.send_message(
#         chat_id=chat_id,
#         text=text,
#         parse_mode="HTML"
#     )



# async def send_alert_price(
#     bot: Bot,
#     chat_id: int,
#     ticker: str,
#     price_level: float,
#     condition: str
# ):
#     """
#     Проверяет цену и отправляет алерт, если условие выполнено.
#     """
#     try:
#         asset = yf.Ticker(ticker)
#         # info = asset.fast_info
        
#         # current_price = info.last_price or info.regular_market_price
#         current_price = await asyncio.to_thread(fetch_current_price, ticker)
        
#         if current_price is None:
#             await bot.send_message(
#                 chat_id=chat_id,
#                 text=f"⚠️ Failed to get price for {ticker}"
#             )
#             return

#         # Проверка условия
#         alert_triggered = False
#         if condition == "above" and current_price >= price_level:
#             alert_triggered = True
#             emoji = "📈"
#             text_condition = "exceeded"
#         elif condition == "below" and current_price <= price_level:
#             alert_triggered = True
#             emoji = "📉"
#             text_condition = "fell below"

#         if alert_triggered:
#             message = (
#                 f"{emoji} <b>Price alert triggered!</b>\n\n"
#                 f"Asset: <b>{ticker}</b>\n"
#                 f"Current price: <b>${current_price:,.4f}</b>\n"
#                 f"Condition: price {text_condition} ${price_level:,.4f}\n\n"
#                 f"Timestamp: {dt.now().strftime('%d.%m.%Y %H:%M')}"
#             )
            
#             await bot.send_message(
#                 chat_id=chat_id,
#                 text=message,
#                 parse_mode="HTML"
#             )
            
#             # Опционально: удаляем алерт после срабатывания (одноразовый)
#             job_id = f"alert_{ticker}_{condition}_{price_level}_{chat_id}"
#             if scheduler.get_job(job_id):
#                 scheduler.remove_job(job_id)

#     except Exception as e:
#         error_text = f"An error occured during checking {ticker}: {str(e)}"
#         print(error_text)  # или логирование
#         try:
#             await bot.send_message(chat_id=chat_id, text=f"⚠️ {error_text}")
#         except:
#             pass



async def send_alert_bordercross(
    bot: Bot,
    chat_id: int,
    ticker: str,
    indicator: str,
    target_value: float,
    condition: str,
    is_one_shot: bool,
    alert_id: str,
    job_id: str,
    params: dict | None = None
):
    """
    Проверяет цену и отправляет алерт, если условие выполнено.
    """

    if params is None:
        params = {}

    try:
        inds = {
                "price": fetch_current_price,
                "rsi": get_current_rsi,
                "macd": get_current_macd,
                "bbands_lower": get_current_bollinger_lower,
                "bbands_upper": get_current_bollinger_upper,
                "atr": get_current_atr
                }
        
        if indicator not in inds:
            raise ValueError(f"Unknown indicator: {indicator}")
        
        func = inds[indicator]
        current_value = await asyncio.to_thread(func, ticker, **params)
        
        if current_value is None:
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Failed to get indicator {indicator} for {ticker}"
            )
            return

        # Проверка условия
        alert_triggered = False
        if condition == "above" and current_value > target_value:
            alert_triggered = True
            emoji = "📈"
            text_condition = "exceeded"
        elif condition == "below" and current_value < target_value:
            alert_triggered = True
            emoji = "📉"
            text_condition = "fell below"

        if alert_triggered:
            message = (
                f"{emoji} <b> Indicator alert triggered!</b>\n\n"
                f"Asset: <b>{ticker}</b>\n"
                f"Current value {indicator}: <b>${current_value:,.4f}</b>\n"
                f"Condition: value {indicator} {text_condition} ${target_value:,.4f}\n\n"
                f"Timestamp: {dt.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML"
            )

            await emit_event(
            "alert_triggered",
            ticker=ticker,
            indicator=indicator,
            value=current_value,
            chat_id=chat_id,
            )
            
            # Опционально: удаляем алерт после срабатывания (одноразовый)
            await mark_alert_triggered(alert_id)
    
            if is_one_shot:
                await deactivate_alert(alert_id)
                from scheduler import scheduler          # ← обязательно локальный импорт
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)

    except Exception as e:
        error_text = f"An error occured during checking {ticker}: {str(e)}"
        print(error_text)  # или логирование
        try:
            await bot.send_message(chat_id=chat_id, text=f"⚠️ {error_text}")
        except:
            pass