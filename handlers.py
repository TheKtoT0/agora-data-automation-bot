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
from servicesnstuff import *
from crud import *
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from states import AssetStates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from scheduler import *
from jobs import *
from inline_keyboards import *
from reply_keyboards import *
from outer import emit_event


rtr = Router(name="user")

menu_keyboard = get_main_menu()

@rtr.message(Command("get_timezone"))
async def cmd_get_timezone(message: Message):
    try:
        timezone = await get_user_timezone(user_id=message.from_user.id)
        await message.answer(f"Your current timezone: <b>{timezone}</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

@rtr.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    chat_id = message.chat.id
    
    await upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        chat_id=chat_id
    )

    await message.answer(
        f"👋 Hi, <b>{user.first_name}</b>!\n\n"
        "I'm your financial assistant. I help track stocks, crypto and your portfolio.\n\n"
        "Commands:\n"
        "• /help — full list\n"
        "• /menu — button menu",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@rtr.message(Command("set_timezone"))
async def cmd_set_timezone(message: Message, command: CommandObject, state: FSMContext):
    try:
        if command.args:

            tz_input = command.args.strip().upper()
            tz_info = parse_utc_offset(tz_input)

            if tz_info is None:
                await message.answer(
                    "❌ Wrong format.\n\n"
                    "Supported:\n"
                    "• UTC\n"
                    "• UTC+3\n"
                    "• UTC-5\n"
                    "• UTC+05:30"
                )
                return

            await update_timezone(message.from_user.id, tz_input)

            offset = tz_info.utcoffset(None)
            hours = int(offset.total_seconds() // 3600)
            sign = "+" if hours >= 0 else ""
            
            await message.answer(
                f"✅ Timezone saved: <b>{tz_input}</b>\n"
                f"UTC offset: {sign}{hours} h.",
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

    if not command.args:
                await message.answer(
                    "Add your timezone.\n\n"
                    "Examples:\n"
                    "• /set_timezone UTC+3\n"
                    "• /set_timezone UTC-5\n"
                    "• /set_timezone UTC"
                )
                await state.set_state(AssetStates.waiting_for_timezone)
                await state.update_data(action="set_timezone")


@rtr.message(Command("menu"))
async def menu(message: Message):
    await message.answer("Choose an action:", reply_markup=get_main_menu())

@rtr.message(AssetStates.waiting_for_timezone)
async def handle_timezone(message: Message, state: FSMContext):
    timezone = message.text.strip().upper()
    tz_info = parse_utc_offset(timezone)
    data = await state.get_data()
    action = data.get("action")

    try:
        if action == "set_timezone":
            await update_timezone(
            user_id=message.from_user.id,
            timezone=timezone
        )

            offset = tz_info.utcoffset(None)
            hours = int(offset.total_seconds() // 3600)
            sign = "+" if hours >= 0 else ""

            await message.answer(
                            f"✅ Timezone saved: <b>{timezone}</b>\n"
                            f"UTC offset: {sign}{hours} h.",
                            parse_mode="HTML"
                        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    finally:
        await state.clear()

@rtr.message(Command("price"))
async def price(message: Message, command: CommandObject, state: FSMContext):
    try:

        if command.args:
            ticker = command.args
            data_ticker = yf.Ticker(ticker).history(period="2d")
            close_today = data_ticker["Close"].iloc[-1]
            close_yesterday = data_ticker["Close"].iloc[-2]
            await message.answer("Asset's price: " + str(close_today) + '\n' + "Change since yesterday: " + str(close_today-close_yesterday))

        if not command.args:
            await message.reply("Send a ticker (for example: AAPL, TSLA, SBER):")
            await state.set_state(AssetStates.waiting_for_ticker)
            await state.update_data(action="price")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

@rtr.message(AssetStates.waiting_for_ticker)
async def handle_1_ticker(message: Message, state: FSMContext):
    ticker = message.text.strip().upper()
    data = await state.get_data()
    action = data.get("action")
    try:
        if action == 'price':
            data_ticker = yf.Ticker(ticker).history(period="2d")
            close_today = data_ticker["Close"].iloc[-1]
            close_yesterday = data_ticker["Close"].iloc[-2]
            await message.answer("Asset's price: " + str(close_today) + '\n' + "Change since yesterday: " + str(close_today-close_yesterday))

        if action == "pricechart":

            chart_buf = await asyncio.to_thread(create_price_chart, ticker)

            if chart_buf is None:
                await message.answer(f"Failed to load data for {ticker}")
                return

            # подход 1
            await message.answer_photo(
                photo=types.BufferedInputFile(
                    file=chart_buf.getvalue(),          # именно .getvalue() → bytes (файлы все дела)
                    filename=f"{ticker}_1y.png"
                ),
                caption="Price chart"
            )

        if action == "metrics":

            info = await asyncio.to_thread(safe_ticker_info, ticker)

            text = (
                f"<b>{ticker}</b> metrics:\n\n"
                f"Open: {info['open']}\n"
                f"Previous Close: {info['previousClose']}\n"
                f"Day Low: {info['dayLow']}\n"
                f"Day High: {info['dayHigh']}\n"
                f"Market Cap: {info['marketCap']}\n"
                f"P/E: {info['trailingPE']}\n"
                f"ROE: {info['returnOnEquity']}\n"
                f"Dividend Yield: {info['dividendYield']}"
            )
            await message.answer(text, parse_mode="HTML")

        if action == "info":
            
            info = await asyncio.to_thread(safe_ticker_info, ticker)

            text = (
                f"<b>{info['displayName']}</b> ({ticker})\n\n"
                f"Sector: {info['sector']}\n"
                f"Industry: {info['industry']}\n"
                f"52-week high: {info['fiftyTwoWeekHigh']}\n"
                f"52-week low: {info['fiftyTwoWeekLow']}\n"
                f"Volume: {info['volume']}"
            )
            await message.answer(text, parse_mode="HTML")

        if action == "get_report":
            await _send_ticker_report(message, ticker)

    except Exception as e:
        await message.answer(f"❌ Error: {e}")

    finally:
        await state.clear()   # обязательно 

@rtr.message(AssetStates.waiting_for_two_tickers)
async def handle_2_tickers(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    
    parts = message.text.strip().upper().split()
    ticker1 = parts[0]
    ticker2 = parts[1]
    logger.info(ticker1, '\n', ticker2, '\n', "asdasd")
    data = await state.get_data()
    action = data.get("action")
    try:
        if action == "compare":

            chart_buf = await asyncio.to_thread(pricechart_comp, ticker1, ticker2)

            if chart_buf is None:
                await message.answer(f"Failed to load data for {ticker1} and {ticker2}")
                return

            await message.answer_photo(
                photo=types.BufferedInputFile(
                    file=chart_buf.getvalue(),          # именно .getvalue() → bytes (файлы все дела)
                    filename=f"{ticker1}_{ticker2}.png"
                ),
                caption=f"Chart for {ticker1} and {ticker2} 1y"
            )

            await message.answer(f"Comparing metrics:")

            chart_buf = await asyncio.to_thread(totable, ticker1, ticker2)

            file = types.BufferedInputFile(
            chart_buf.getvalue(), 
            filename=f"{ticker1}_vs_{ticker2}_comparison.xlsx"
            )
            
            await message.answer_document(
                document=file,
                caption=f"Comparing {ticker1} and {ticker2}"
            )

    except Exception as e:
        await message.answer(f"❌ Error: {e}")

    finally:
        await state.clear()   # <---- обязательно 

@rtr.message(Command("plottest"))
async def send_plot(message: types.Message):
    photo_bytes = create_plot()
    
    await message.answer_photo(
        photo=types.BufferedInputFile(
            file=photo_bytes.read(),
            filename="chart.png"          # Telegram любит расширение
        ),
        caption="There's your chart for sin(x) and cos(x) 🎨"
    )

@rtr.message(Command("pricechart"))
async def cmd_price(message: Message, command: CommandObject, state: FSMContext):
    if command.args:

        parts = command.args.split()
        ticker = parts[0].upper()
        period = parts[1] if len(parts) > 1 else "1y"

        # Шпора на периоды yfinance: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        chart_buf = await asyncio.to_thread(create_price_chart, ticker, period)

        if chart_buf is None:
            await message.answer(f"Failed to load data for {ticker}")
            return

        # подход 1
        await message.answer_photo(
            photo=types.BufferedInputFile(
                file=chart_buf.getvalue(),          # именно .getvalue() → bytes (файлы все дела)
                filename=f"{ticker}_{period}.png"
            ),
            caption="Price chart"
        )

    else:
        await message.reply("Send a ticker (for example: AAPL, TSLA, SBER):")
        await state.set_state(AssetStates.waiting_for_ticker)
        await state.update_data(action="pricechart")

@rtr.message(Command("compare"))
async def cmd_compare(message: Message, command: CommandObject, state: FSMContext):
    if command.args:

        parts = command.args.split()
        ticker1 = parts[0].upper()
        ticker2 = parts[1].upper()

        chart_buf = await asyncio.to_thread(pricechart_comp, ticker1, ticker2)

        if chart_buf is None:
            await message.answer(f"Failed to load data for {ticker1} and {ticker2}")
            return

        await message.answer_photo(
            photo=types.BufferedInputFile(
                file=chart_buf.getvalue(),          # именно .getvalue() → bytes (файлы все дела)
                filename=f"{ticker1}_{ticker2}.png"
            ),
            caption=f"Chart for {ticker1} and {ticker2} 1y"
        )

        await message.answer(f"Comparing metrics:")

        chart_buf = await asyncio.to_thread(totable, ticker1, ticker2)

        file = types.BufferedInputFile(
        chart_buf.getvalue(), 
        filename=f"{ticker1}_vs_{ticker2}_comparison.xlsx"
        )
        
        await message.answer_document(
            document=file,
            caption=f"Comparing {ticker1} and {ticker2}"
        )

    else:
        await message.reply("Send tickers (for example: AAPL, TSLA, SBER) with a spacebar:")
        await state.set_state(AssetStates.waiting_for_two_tickers)
        await state.update_data(action="compare")

@rtr.message(Command("metrics"))
async def metriki(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        ticker = command.args
        info = await asyncio.to_thread(safe_ticker_info, ticker)

        text = (
            f"<b>{ticker}</b> metrics:\n\n"
            f"Open: {info['open']}\n"
            f"Previous Close: {info['previousClose']}\n"
            f"Day Low: {info['dayLow']}\n"
            f"Day High: {info['dayHigh']}\n"
            f"Market Cap: {info['marketCap']}\n"
            f"P/E: {info['trailingPE']}\n"
            f"ROE: {info['returnOnEquity']}\n"
            f"Dividend Yield: {info['dividendYield']}"
        )
        await message.answer(text, parse_mode="HTML")

    else:
        await message.reply("Send a ticker (for example: AAPL, TSLA, SBER):")
        await state.set_state(AssetStates.waiting_for_ticker)
        await state.update_data(action="metrics")

@rtr.message(Command("get_report_portfolio"))
async def send_report_portfolio(message: Message):
    user_id = message.chat.id
    filename = f"{user_id}_portfolio_report.pdf"
    pdf_bytes = await generate_portfolio_report(user_id)

    await message.answer_document(
        document=types.BufferedInputFile(file=pdf_bytes,
                                                       filename=filename),
                    caption=f"Your portfolio report"
    )


@rtr.message(Command("info"))
async def info(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        ticker = command.args
        info = await asyncio.to_thread(safe_ticker_info, ticker)

        text = (
            f"<b>{info['displayName']}</b> ({ticker})\n\n"
            f"Sector: {info['sector']}\n"
            f"Industry: {info['industry']}\n"
            f"52-week high: {info['fiftyTwoWeekHigh']}\n"
            f"52-week low: {info['fiftyTwoWeekLow']}\n"
            f"Volume: {info['volume']}"
        )
        await message.answer(text, parse_mode="HTML")

    else:
        await message.reply("Send a ticker (for example: AAPL, TSLA, SBER):")
        await state.set_state(AssetStates.waiting_for_ticker)
        await state.update_data(action="info")

@rtr.message(Command("subscribe_price"))
async def cmd_subscribe_price(message: Message, state: FSMContext):
    await message.answer("Send ticker and timestamp:\nAAPL 9:30")
    await state.set_state(AssetStates.waiting_for_schedule_command_price)

@rtr.message(AssetStates.waiting_for_schedule_command_price)
async def process_schedule_command_price(message: Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        ticker = parts[0].upper()
        time_str = parts[1]
        hour, minute = map(int, time_str.split(':'))

        # 1. Сохраняем в БД
        sub_id = await create_subscription(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            ticker=ticker,
            sub_type="price",
            hour=hour,
            minute=minute,
        )

        job_id = f"daily_price_{sub_id}"

        await emit_event(
        "subscription_created",
        ticker=ticker,
        sub_type=job_id,
        user_id=message.from_user.id,
        )

        # 2. Создаём job
        await add_daily_price_job(
            bot=bot,
            chat_id=message.chat.id,
            ticker=ticker,
            hour=hour,
            minute=minute,
            job_id=job_id
        )

        # 3. Сохраняем job_id
        await update_subscription_job_id(sub_id, job_id)

        user_tz = await get_user_timezone(message.from_user.id)

        await message.answer(
            f"✅ Subscription created!\n"
            f"Daily at <b>{hour:02d}:{minute:02d}</b> ({user_tz}) "
            f"I will send the price of <b>{ticker}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    finally:
        await state.clear()


        
@rtr.message(Command("subscribe_chart"))
async def cmd_subscribe_chart(message: Message, state: FSMContext):
    await message.answer("Send ticker and timestamp:\nAAPL 9:30")
    await state.set_state(AssetStates.waiting_for_schedule_command_chart)



@rtr.message(AssetStates.waiting_for_schedule_command_chart)
async def process_schedule_command_chart(message: Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        ticker = parts[0].upper()
        time_str = parts[1]

        hour, minute = map(int, time_str.split(':'))

        sub_id = await create_subscription(
            user_id=message.from_user.id,
            chat_id = message.chat.id,
            ticker = ticker,
            sub_type='chart',
            hour = hour,
            minute = minute
        )

        job_id = f'daily_chart_{sub_id}'

        await emit_event(
        "subscription_created",
        ticker=ticker,
        sub_type=job_id,
        user_id=message.from_user.id,
        )

        await add_daily_chart_job(bot=bot, chat_id=message.chat.id, ticker=ticker, hour=hour, minute=minute, job_id=job_id)

        user_tz = await get_user_timezone(message.from_user.id)

        await message.answer(
            f"✅ Subscription created!\n"
            f"Daily at <b>{hour:02d}:{minute:02d}</b> ({user_tz}) "
            f"I will send chart of <b>{ticker}</b>",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    finally:
        await state.clear()




@rtr.message(Command("subscribe_report_ticker"))
async def cmd_subscribe_report_ticker(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    if command.args:
        try:
            parts = command.args.strip().split()
            ticker = parts[0].upper()
            time_str = parts[1]
    
            hour, minute = map(int, time_str.split(':'))
    
            sub_id = await create_subscription(
                user_id=message.from_user.id,
                chat_id = message.chat.id,
                ticker = ticker,
                sub_type='report',
                hour = hour,
                minute = minute
            )
    
            job_id = f'daily_report_ticker_{sub_id}'

            await emit_event(
            "subscription_created",
            ticker=ticker,
            sub_type=job_id,
            user_id=message.from_user.id,
            )

            await update_subscription_job_id(sub_id, job_id)
    
            await add_daily_report_ticker_job(bot=bot, chat_id=message.chat.id, ticker=ticker, hour=hour, minute=minute, job_id=job_id)
    
            user_tz = await get_user_timezone(message.from_user.id)
    
            await message.answer(
                f"✅ Subscription created!\n"
                f"Daily at <b>{hour:02d}:{minute:02d}</b> ({user_tz}) "
                f"I will send a report for <b>{ticker}</b>",
                parse_mode="HTML"
            )
    
        except Exception as e:
            await message.answer(f"❌ Error: {e}")

    if not command.args:
        await message.answer("Send ticker and timestamp:\nAAPL 9:30")
        await state.set_state(AssetStates.waiting_for_schedule_command_report_ticker)

@rtr.message(AssetStates.waiting_for_schedule_command_report_ticker)
async def process_schedule_report_ticker(message: Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        ticker = parts[0].upper()
        time_str = parts[1]

        hour, minute = map(int, time_str.split(':'))

        sub_id = await create_subscription(
            user_id=message.from_user.id,
            chat_id = message.chat.id,
            ticker = ticker,
            sub_type='report',
            hour = hour,
            minute = minute
        )

        job_id = f'daily_report_ticker_{sub_id}'

        await emit_event(
        "subscription_created",
        ticker=ticker,
        sub_type=job_id,
        user_id=message.from_user.id,
        )

        await update_subscription_job_id(sub_id, job_id)

        await add_daily_report_ticker_job(bot=bot, chat_id=message.chat.id, ticker=ticker, hour=hour, minute=minute, job_id=job_id)

        user_tz = await get_user_timezone(message.from_user.id)

        await message.answer(
            f"✅ Subscription created!\n"
            f"Daily at <b>{hour:02d}:{minute:02d}</b> ({user_tz}) "
            f"I will send a report for <b>{ticker}</b>",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    finally:
        await state.clear()

        
@rtr.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Financial Telegram Bot</b>\n\n"
        "Here are all available commands:\n\n"

        "📌 <b>Main commands</b>\n"
        "/start — greeting and registration\n"
        "/menu — show main menu with buttons\n"
        "/help — show this message\n\n"

        "💰 <b>Ticker information</b>\n"
        "/price [TICKER] — current price + change\n"
        "/metrics [TICKER] — key financial metrics\n"
        "/info [TICKER] — company info (sector, industry, etc.)\n"
        "/pricechart [TICKER] [PERIOD] — price chart\n"
        "   Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max\n\n"

        "🔄 <b>Comparison</b>\n"
        "/compare TICKER1 TICKER2 — comparison chart + metrics table\n\n"

        "🔔 <b>Subscriptions & Alerts</b>\n"
        "/subscribe_report_ticker TICKER HH:MM — daily PDF report for ticker\n"
        "/set_alert TICKER INDICATOR CONDITION VALUE — create alert\n"
        "   Example: AAPL price above 500\n"
        "   Indicators: price, rsi, macd, bbands_upper, bbands_lower, atr\n\n"

        "🌍 <b>Timezone</b>\n"
        "/set_timezone UTC+3 — set your timezone\n"
        "/get_timezone — show current timezone\n\n"

        "📁 <b>Portfolio</b>\n"
        "/add_to_portfolio TICKER AMOUNT [BUY_PRICE] — add position\n"
        "/remove_from_portfolio TICKER AMOUNT — remove position\n"
        "/portfolio — show your portfolio\n"
        "/get_report_portfolio — PDF report for your portfolio\n\n"

        "❗ <b>Important</b>\n"
        "• If you don't specify arguments after the command — the bot will ask for them separately\n"
        "• Supported: stocks, ETFs and crypto (e.g. AAPL, SBER.ME, BTC-USD)\n"
        "• Time in subscriptions is based on your timezone\n"
        "• If the bot is waiting for input, send any valid ticker or use the menu buttons\n"
    )

    await message.answer(help_text, parse_mode="HTML", disable_web_page_preview=True)



@rtr.message(Command("add_to_portfolio"))
async def cmd_add_to_portfolio(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        try:
            parts = command.args.strip().split()
            ticker = parts[0].upper()
            quantity = float(parts[1])
            avg_price = float(parts[2]) if len(parts) > 2 else None

            if avg_price is None:
                # Если цену не указали - берём текущую
                current = await get_price(ticker)
                avg_price = current['price']

            await add_to_portfolio(
                user_id=message.from_user.id,
                ticker=ticker,
                quantity=quantity,
                avg_buy_price=avg_price
            )

            await message.answer(f"✅ Position added:\n{ticker} × {quantity} for ${avg_price:.2f}")

        except Exception as e:
            await message.answer(f"❌ Error: {e}\nCorrect format: TICKER AMOUNT BUY_PRICE")

    if not command.args:
            await message.answer("Using:\n/add_to_portfolio TICKER AMOUNT BUY_PRICE")
            await state.set_state(AssetStates.waiting_for_add_to_portfolio)


@rtr.message(AssetStates.waiting_for_add_to_portfolio)
async def process_schedule_command_add_to_portfolio(message: Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        ticker = parts[0].upper()
        quantity = float(parts[1])
        avg_price = float(parts[2]) if len(parts) > 2 else None

        if avg_price is None:
            # Если цену не указали - берём текущую
            current = await get_price(ticker)
            avg_price = current['price']

        await add_to_portfolio(
            user_id=message.from_user.id,
            ticker=ticker,
            quantity=quantity,
            avg_buy_price=avg_price
        )

        await message.answer(f"✅ Position added:\n{ticker} × {quantity} for ${avg_price:.2f}")

    except Exception as e:
        await message.answer(f"❌ Error: {e}\nCorrect format: TICKER AMOUNT BUY_PRICE")

    finally:
            await state.clear()

@rtr.message(Command("remove_from_portfolio"))
async def cmd_remove_from_portfolio(message: Message, command: CommandObject, state: FSMContext):

    if command.args:
        try:
            parts = command.args.strip().split()
            ticker = parts[0].upper()
            quantity = float(parts[1])

            await remove_from_portfolio(
                user_id=message.from_user.id,
                ticker=ticker,
                quantity=quantity
            )

            await message.answer(f"✅ Position removed:\n{ticker} × {quantity}")

        except Exception as e:
            await message.answer(f"❌ Error: {e}\nCorrect format: TICKER AMOUNT")

    if not command.args:
                await message.answer("Using:\n/remove_from_portfolio TICKER AMOUNT\n\nExample:\n/remove_from_portfolio AAPL 3")
                await state.set_state(AssetStates.waiting_for_remove_from_portfolio)


@rtr.message(AssetStates.waiting_for_remove_from_portfolio)
async def process_schedule_command_remove_from_portfolio(message: Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        ticker = parts[0].upper()
        quantity = float(parts[1])

        await remove_from_portfolio(
            user_id=message.from_user.id,
            ticker=ticker,
            quantity=quantity
        )

        await message.answer(f"✅ Position removed:\n{ticker} × {quantity}")

    except Exception as e:
        await message.answer(f"❌ Error: {e}\nCorrect format: TICKER AMOUNT")
    finally:
        await state.clear()


@rtr.message(Command("portfolio"))
async def cmd_portfolio(message: Message):
    portfolio = await get_portfolio(message.from_user.id)
    
    if not portfolio:
        await message.answer("📭 Your portfolio is empty.\nUse /add_to_portfolio")
        return

    text = "📊 <b>Your portfolio:</b>\n\n"
    total_value = 0

    for pos in portfolio:
        ticker = pos['ticker']
        qty = pos['quantity']
        avg = pos['avg_buy_price']
        
        current_data = await get_price(ticker)
        current_price = current_data.get('price', 0)
        
        value = qty * current_price
        total_value += value
        pnl = (current_price - avg) * qty
        pnl_percent = ((current_price - avg) / avg * 100) if avg else 0

        text += (
            f"<b>{ticker}</b> × {qty:.4f}\n"
            f"💰 Average price: ${avg:.2f} → ${current_price:.2f}\n"
            f"📈 P&L: {pnl:+.2f}$ ({pnl_percent:+.1f}%)\n"
            f"💵 Current price: ${value:.2f}\n\n"
        )

    text += f"<b>Total:</b> ${total_value:.2f}"
    
    await message.answer(text, parse_mode="HTML")


@rtr.message(Command("set_alert"))
async def cmd_set_alert(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    if command.args:

        try:
            parts = command.args.strip().split()
            ticker = parts[0].upper()
            indicator = parts[1]
            condition = parts[2]
            value = float(parts[3])
    
            alert_id = await create_alert(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                ticker=ticker,
                indicator=indicator,
                condition=condition,
                target_value=value,
                is_one_shot=True
            )
    
            job_id = f"alert_{alert_id}"
    
            await add_ind_alert_job(  # или отдельная функция
                bot=bot,
                chat_id=message.chat.id,
                ticker=ticker,
                indicator=indicator,
                target_value=value,
                condition=condition,
                job_id=job_id,
                alert_id=alert_id,   # передаём, чтобы job знал, какой алерт обновлять
            )
    
            await update_alert_job_id(alert_id, job_id)
            
            await message.answer(
                f"✅ Alert created!\n"
                f"Each time when {ticker} {condition} {value} an alert will be sent"
            )
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")

    if not command.args:
        await message.answer("Send ticker, indicator, condition:\nAAPL price above 500 or TSLA bbands_lower below 350")
        await state.set_state(AssetStates.waiting_for_set_alert)

@rtr.message(AssetStates.waiting_for_set_alert)
async def process_set_alert(message: Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        ticker = parts[0].upper()
        indicator = parts[1]
        condition = parts[2]
        value = float(parts[3])

        alert_id = await create_alert(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            ticker=ticker,
            indicator=indicator,
            condition=condition,
            target_value=value,
            is_one_shot=True
        )

        job_id = f"alert_{alert_id}"

        await add_ind_alert_job(  # или отдельная функция
            bot=bot,
            chat_id=message.chat.id,
            ticker=ticker,
            indicator=indicator,
            target_value=value,
            condition=condition,
            job_id=job_id,
            alert_id=alert_id,   # передаём, чтобы job знал, какой алерт обновлять
        )

        await update_alert_job_id(alert_id, job_id)
        
        await message.answer(
            f"✅ Alert created!\n"
            f"Each time when {ticker} {condition} {value} an alert will be sent"
        )
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    finally:
        await state.clear()




@rtr.message(Command("my_subscriptions"))
async def cmd_my_subscriptions(message: Message):
    try:
        subs = await get_user_subscriptions(message.from_user.id)

        if not subs:
            await message.answer("📭 You have no active subscriptions.")
            return

        text = "📋 <b>Your active subscriptions:</b>\n\n"
        for sub in subs:
            text += (
                f"🔹 <b>ID {sub['id']}</b> | {sub['sub_type'].upper()}\n"
                f"   Ticker: <b>{sub['ticker']}</b>\n"
                f"   Time: {sub['hour']:02d}:{sub['minute']:02d}\n\n"
            )

        text += "To remove: /remove_subscription ID"
        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Error: {e}")

@rtr.message(Command("remove_subscription"))
async def _remove_subscription(message: Message, command: CommandObject):
    sub_id = int(command.args)
    subs = await get_user_subscriptions(message.from_user.id, only_active=False)
    sub = next((s for s in subs if s["id"] == sub_id), None)
    
    await deactivate_subscription(sub_id)

    if sub and sub.get("job_id"):
        from scheduler import scheduler
        if scheduler.get_job(sub["job_id"]):
            scheduler.remove_job(sub["job_id"])

    await message.answer(f"✅ Subscription <b>#{sub_id}</b> removed.", parse_mode="HTML")


@rtr.message(AssetStates.waiting_for_remove_subscription)
async def process_remove_subscription(message: Message, state: FSMContext):
    try:
        sub_id = int(message.text.strip())
        await _remove_subscription(message, sub_id)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    finally:
        await state.clear()


@rtr.message(Command("my_alerts"))
async def cmd_my_alerts(message: Message):
    try:
        alerts = await get_user_alerts(message.from_user.id)

        if not alerts:
            await message.answer("📭 You have no active alerts.")
            return

        text = "🔔 <b>Your active alerts:</b>\n\n"
        for alert in alerts:
            text += (
                f"🔹 <b>ID {alert['id']}</b>\n"
                f"   {alert['ticker']} | {alert['indicator']} {alert['condition']} {alert['target_value']}\n\n"
            )

        text += "To remove: /remove_alert ID"
        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Error: {e}")




@rtr.message(Command("remove_alert"))
async def cmd_remove_alert(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        try:
            alert_id = int(command.args.strip())
            await _remove_alert(message, alert_id)
        except Exception as e:
            await message.answer(f"❌ Error: {e}")
    else:
        await message.answer("Send alert ID to remove:\nExample: 5")
        await state.set_state(AssetStates.waiting_for_remove_alert)


@rtr.message(AssetStates.waiting_for_remove_alert)
async def process_remove_alert(message: Message, state: FSMContext):
    try:
        alert_id = int(message.text.strip())
        await _remove_alert(message, alert_id)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    finally:
        await state.clear()


async def _remove_alert(message: Message, alert_id: int):
    """Общая логика удаления алерта"""
    await deactivate_alert(alert_id)

    from scheduler import scheduler
    job_id = f"alert_{alert_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    await message.answer(f"✅ Alert <b>#{alert_id}</b> removed.", parse_mode="HTML")

@rtr.message(Command("get_report"))
async def cmd_get_report(message: Message, command: CommandObject, state: FSMContext):
    if not command.args:
        await message.answer("Send a ticker:\nExample: AAPL")
        await state.set_state(AssetStates.waiting_for_ticker)
        await state.update_data(action="get_report")
        return

    ticker = command.args.strip().upper()
    await _send_ticker_report(message, ticker)


async def _send_ticker_report(message: Message, ticker: str):
    try:
        await message.answer(f"⏳ Generating report for <b>{ticker}</b>...", parse_mode="HTML")

        pdf_bytes = generate_report_no_save(ticker)
        filename = f"{ticker}_report.pdf"

        await message.answer_document(
            document=types.BufferedInputFile(
                file=pdf_bytes,
                filename=filename
            ),
            caption=f"📄 Report for <b>{ticker}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Failed to generate report for {ticker}:\n{e}")

@rtr.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Nothing to cancel.")
        return

    await state.clear()
    await message.answer("✅ Action cancelled.")