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
from datetime import datetime, timezone, timedelta
import re
from pandas import ExcelWriter
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from crud import get_portfolio, get_portfolio_position

import logging

logger = logging.getLogger(__name__)


def parse_utc_offset(timezone_str: str | None) -> timezone | None:
    """
    Парсит строки вида:
        "UTC", "UTC+3", "UTC-5", "UTC+0", "UTC+05:30", "UTC-4"
    и возвращает datetime.timezone с правильным offset.
    Если не удалось распарсить — возвращает None.
    """
    if not timezone_str:
        return None

    tz = str(timezone_str).strip().upper().replace(" ", "")

    # Специальный случай чистого "UTC"
    if tz == "UTC":
        return timezone.utc

    match = re.match(r"UTC([+-])(\d{1,2})(?::(\d{2}))?$", tz)
    if not match:
        return None

    sign = match.group(1)
    hours = int(match.group(2))
    minutes = int(match.group(3)) if match.group(3) else 0

    # Защита от совсем диких значений
    if hours > 23 or minutes > 59:
        return None

    offset_minutes = hours * 60 + minutes
    if sign == "-":
        offset_minutes = -offset_minutes

    return timezone(timedelta(minutes=offset_minutes))

def create_plot():
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    
    x = np.linspace(0, 10, 500)
    y1 = np.sin(x)
    y2 = np.cos(x)
    
    ax.plot(x, y1, label='sin(x)', linewidth=2)
    ax.plot(x, y2, label='cos(x)', linewidth=2)
    ax.set_title("sin & cos test plot", fontsize=14)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=120, transparent=True)
    buf.seek(0)
    plt.close(fig)          # ВАЖНОО
    
    return buf

def get_price_sync(ticker: str):
    data_ticker = yf.Ticker(ticker).history(period="2d")
    close_today = data_ticker["Close"].iloc[-1]
    close_yesterday = data_ticker["Close"].iloc[-2]
    open_today = data_ticker["Close"].iloc[-1]
    open_yesterday = data_ticker["Close"].iloc[-2]
    # return ("Цена финансового актива: " + str(close_today) + '\n' + "Изменение со вчера: " + str(close_today-close_yesterday))
    return {
        "price": close_today,
        "change": close_today-close_yesterday,
        "close today": close_today,
        "close yesterday": close_yesterday,
        "open today": open_today,
        "open yesterday": open_yesterday
        # ... добавить по необходимости еще чо-то
    }

async def get_price(ticker: str) -> dict:
    return await asyncio.to_thread(get_price_sync, ticker)

def fetch_current_price_OLD(ticker):
    asset = yf.Ticker(ticker)
    info = asset.fast_info
    return info.get('last_price') or info.get('regular_market_price') or asset.history(period="5d", interval="1m")

def fetch_current_price(ticker: str) -> float | None:
    try:
        ticker = ticker.upper().strip()
        asset = yf.Ticker(ticker)

        # 1. Самый надёжный способ — последняя минутка
        hist = asset.history(period="1d", interval="1m")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])

        # 2. fast_info
        fi = getattr(asset, "fast_info", None)
        if fi:
            for key in ("last_price", "regular_market_price", "previous_close"):
                value = fi.get(key) if hasattr(fi, "get") else getattr(fi, key, None)
                if value is not None:
                    return float(value)

        # 3. Обычный info
        info = asset.info
        for key in ("currentPrice", "regularMarketPrice", "previousClose", "open"):
            if key in info and info[key] is not None:
                return float(info[key])

        # 4. Последний fallback — дневные данные
        hist_daily = asset.history(period="5d")
        if hist_daily is not None and not hist_daily.empty:
            return float(hist_daily["Close"].iloc[-1])

        return None

    except Exception as e:
        logger.error(f"[fetch_current_price] Error for {ticker}: {e}", exc_info=True)
        return None

async def get_pricechart_daily(ticker: str, style: str = "classic"):
    data_ticker = yf.Ticker(ticker).history(period="2d")
    period = "2d"
    df = yf.download(ticker, period=period, progress=False, threads=False)
        
    if df.empty or len(df) < 2:
        return None

    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

    try:
        period = period.lower().strip()
        if period not in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}:
            period = "2d"  

        df = yf.download(ticker, period=period, progress=False, threads=False)
        
        if df.empty or len(df) < 2:
            return None

        plt.style.use(style)
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        close = df['Close'].to_numpy().ravel()

        ax.plot(df.index, close, label='Close', color='#2962ff', linewidth=2)
        ax.fill_between(df.index, close, alpha=0.08, color='#2962ff')

        ax.set_title(f"{ticker.upper()}  |  {period}", fontsize=16, pad=15)
        ax.set_xlabel("Date")
        ax.set_ylabel("Price (USD)")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend()

        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)

        plt.close(fig)          # ← обязательно освобождаем память!

        return buf
    
    except Exception as e:
        logger.error(f"Ошибка построения графика {ticker}: {e}", exc_info=True)
        return None

# get_pricechart_daily("AAPL")

def pricechart_comp(ticker1: str, ticker2: str, period: str = "1y", style: str = "classic"):
    try:
        period = period.lower().strip()
        if period not in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}:
            period = "1y"  # 

        df1 = yf.download(ticker1, period=period, progress=False, threads=False)
        df2 = yf.download(ticker2, period=period, progress=False, threads=False)

        if df1.empty or len(df1) < 2:
            return None
        
        if df2.empty or len(df2) < 2:
            return None

        plt.style.use(style)
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        close1 = df1['Close'].to_numpy().ravel()
        close2 = df2['Close'].to_numpy().ravel()
        ax.plot(df1.index, close1, label='Close', color='#2962ff', linewidth=2)
        ax.fill_between(df1.index, close1, alpha=0.08, color='#2962ff')

        ax.plot(df2.index, close2, label='Close', color="#ff2929", linewidth=2)
        ax.fill_between(df2.index, close2, alpha=0.08, color="#ff2929")

        ax.set_title(f"{ticker2.upper()} and {ticker1.upper()}  |  {period}", fontsize=16, pad=15)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Цена (USD)")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend()

        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.15)
        buf.seek(0)

        plt.close(fig)          

        return buf

    except Exception as e:
        logger.error(f"Ошибка построения графика {ticker1}: {e}", exc_info=True)
        return None

def create_price_chart(ticker: str, period: str = "1y", style: str = "classic"):
    try:
        period = period.lower().strip()
        if period not in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}:
            period = "1y"

        df = yf.download(
            ticker,
            period=period,
            progress=False,
            threads=False,
            auto_adjust=True,
            multi_level_index=False,   # важно
        )

        if df is None or df.empty or len(df) < 2:
            return None

        plt.style.use(style)
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        close = df["Close"].to_numpy().ravel()

        ax.plot(df.index, close, label="Close", color="#2962ff", linewidth=2)
        ax.fill_between(df.index, close, alpha=0.08, color="#2962ff")

        ax.set_title(f"{ticker.upper()}  |  {period}", fontsize=16, pad=15)
        ax.set_xlabel("Date")
        ax.set_ylabel("Price (USD)")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend()

        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf

    except Exception as e:
        logger.error(f"Ошибка построения графика {ticker}: {e}", exc_info=True)
        return None

def safe_ticker_info(ticker: str) -> dict:
    """Безопасно достаёт основные поля из yfinance.info"""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    def g(*keys, default="N/A"):
        for k in keys:
            v = info.get(k)
            if v is not None:
                return v
        return default

    return {
        "open": g("open", "regularMarketOpen"),
        "previousClose": g("previousClose", "regularMarketPreviousClose"),
        "dayLow": g("dayLow", "regularMarketDayLow"),
        "dayHigh": g("dayHigh", "regularMarketDayHigh"),
        "marketCap": g("marketCap"),
        "trailingPE": g("trailingPE", "forwardPE"),
        "returnOnEquity": g("returnOnEquity"),
        "dividendYield": g("dividendYield"),
        "displayName": g("displayName", "shortName", "longName", default=ticker),
        "sector": g("sector"),
        "industry": g("industry"),
        "fiftyTwoWeekHigh": g("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": g("fiftyTwoWeekLow"),
        "volume": g("volume", "regularMarketVolume"),
    }

def totable(ticker1: str, ticker2: str):
    def safe_info(ticker: str) -> dict:
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}

        def g(*keys):
            for k in keys:
                v = info.get(k)
                if v is not None:
                    return v
            return None

        return {
            "Open": g("open", "regularMarketOpen"),
            "Previous Close": g("previousClose", "regularMarketPreviousClose"),
            "Day Low": g("dayLow", "regularMarketDayLow"),
            "Day High": g("dayHigh", "regularMarketDayHigh"),
            "Market Cap": g("marketCap"),
            "Trailing PE": g("trailingPE", "forwardPE"),
            "Return on Equity": g("returnOnEquity"),
            "Dividend Yield": g("dividendYield"),
        }

    info1 = safe_info(ticker1)
    info2 = safe_info(ticker2)

    # Заменяем None на "N/A"
    def fmt(v):
        if v is None:
            return "N/A"
        if isinstance(v, float):
            if abs(v) >= 1_000_000_000:
                return f"{v / 1_000_000_000:.2f}B"
            if abs(v) >= 1_000_000:
                return f"{v / 1_000_000:.2f}M"
            return f"{v:.4f}" if abs(v) < 1 else f"{v:.2f}"
        return str(v)

    data = {
        "Metric": list(info1.keys()),
        ticker1: [fmt(v) for v in info1.values()],
        ticker2: [fmt(v) for v in info2.values()],
    }

    df = pd.DataFrame(data)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Comparison", index=False)
        worksheet = writer.sheets["Comparison"]

        for i, col in enumerate(df.columns):
            # Безопасный расчёт ширины колонки
            col_values = df[col].fillna("").astype(str)
            max_len = max(col_values.map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, max_len)

    buf.seek(0)
    return buf

def generate_report_no_save(ticker: str):
    # получаем данные
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="7d")   # последние 7 дней

    # Подготовка истории
    hist = hist[['Close']].copy()
    hist['Change'] = hist['Close'].pct_change() * 100

    history_data = []
    for date, row in hist.iterrows():
        history_data.append({
            "date": date.strftime("%d.%m"),
            "close": round(row['Close'], 2),
            "change": round(row['Change'], 2) if not pd.isna(row['Change']) else 0
        })

    # Дата для шаблона
    data = {
        "ticker": ticker,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "metrics": {
            "Current price": f"${info.get('currentPrice', '-')}",
            "Fifty two weeks high": f"${info.get('fiftyTwoWeekHigh', '-')}",
            "Fifty two weeks low": f"${info.get('fiftyTwoWeekLow', '-')}",
            "market cap.": f"{info.get('marketCap', 0) / 1_000_000_000:.1f} bil",
            "P/E": round(info.get('trailingPE', 0), 2) or "-",
        },
        "history": history_data
    }

    #Рендер HTM;
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report.html")
    html_string = template.render(**data)
    
    pdf_bytes = HTML(string=html_string).write_pdf(None)
    return pdf_bytes



async def portfolio_into_tickerset(user_id: int):
    portfolio = await get_portfolio(user_id=user_id)
    alltick_arr = []

    for i in portfolio:
        tick = i["ticker"]
        weight = i["quantity"]
        avg_temp = i["avg_buy_price"]
        alltick_arr.append([tick, weight, avg_temp])

    hist_port = {}
    for i in alltick_arr:
        hist_temp = yf.Ticker(i[0]).history(period='7d')
        hist_temp = hist_temp[['Close']].copy()
        hist_temp['Change'] = hist_temp['Close'].pct_change() * 100

        history_data = []
        for date, row in hist_temp.iterrows():
            history_data.append({
                "date": date.strftime("%d.%m"),
                "close": round(row['Close'], 2),
                "change": round(row['Change'], 2) if not pd.isna(row['Change']) else 0
            })

        hist_port[i[0]] = history_data  

    # info_port
    # history_port

    return hist_port, alltick_arr







def calculate_portfolio_7d(hist_port: dict, alltick_arr: list) -> dict:
    """
    Возвращает:
    - daily_values: список стоимости портфеля по дням
    - avg_value_7d: средняя стоимость портфеля за 7 дней
    - change_7d_pct: изменение стоимости за 7 дней (%)
    - change_7d_abs: изменение в деньгах
    - per_ticker: средняя цена и изменение по каждому тикеру
    """
    
    # quantity по тикеру
    qty = {ticker: quantity for ticker, quantity, _ in alltick_arr}

    # qty = {}
    # for ticker, quantity, _ in alltick_arr:
    #     qty[ticker] = quantity
    
    # Собираем все даты (берём из первого тикера, т.к. период одинаковый)
    first_ticker = next(iter(hist_port))
    dates = [day["date"] for day in hist_port[first_ticker]]

    # dates = []
    # for day in hist_port[first_ticker]:
    #     dates.append(day["date"])
    
    daily_values = []
    #Получаем цены портфеля за каждый день
    for i, date in enumerate(dates):
        day_value = 0.0
        for ticker, history in hist_port.items():
            close = history[i]["close"]
            day_value += qty[ticker] * close
        daily_values.append({
            "date": date,
            "value": round(day_value, 2)
        })
    
    values = [d["value"] for d in daily_values]

    # values = []
    # for d in daily_values:
    #     values.append(d["value"])
    
    avg_value_7d = round(sum(values) / len(values), 2)
    change_7d_abs = round(values[-1] - values[0], 2)
    change_7d_pct = round((values[-1] / values[0] - 1) * 100, 2) if values[0] else 0.0
    
    #по каждому тикеру - средняя цена и изменение за 7 дней
    per_ticker = {}
    for ticker, history in hist_port.items():
        closes = [d["close"] for d in history]
        avg_price = round(sum(closes) / len(closes), 2)
        change_pct = round((closes[-1] / closes[0] - 1) * 100, 2) if closes[0] else 0.0
        
        per_ticker[ticker] = {
            "avg_price_7d": avg_price,
            "change_7d_pct": change_pct,
            "current_price": closes[-1],
            "quantity": qty[ticker],
            "current_value": round(qty[ticker] * closes[-1], 2)
        }
    
    return {
        "daily_values": daily_values,
        "avg_value_7d": avg_value_7d,
        "current_value": values[-1],
        "value_7d_ago": values[0],
        "change_7d_abs": change_7d_abs,
        "change_7d_pct": change_7d_pct,
        "per_ticker": per_ticker
    }

async def generate_portfolio_report(user_id: int) -> bytes:
    # 1. Получаем данные
    hist_port, alltick_arr = await portfolio_into_tickerset(user_id)
    calc = calculate_portfolio_7d(hist_port, alltick_arr)

    # 2. Готовим данные для шаблона
    data = {
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "current_value": calc["current_value"],
        "avg_value_7d": calc["avg_value_7d"],
        "value_7d_ago": calc["value_7d_ago"],
        "change_7d_abs": calc["change_7d_abs"],
        "change_7d_pct": calc["change_7d_pct"],
        "daily_values": calc["daily_values"],
        "per_ticker": calc["per_ticker"],
    }

    # 3. Рендерим
    env = Environment(loader=FileSystemLoader("templates"))
    env.globals["enumerate"] = enumerate          # ОЧЕНЬВАЖНО ОБЪЯВИТЬ enumerate JINJA ЕГО НЕ ЗНАЕТ
    template = env.get_template("portfolio_report.html")
    html_string = template.render(**data)

    # 4. В PDF
    pdf_bytes = HTML(string=html_string).write_pdf(None)
    return pdf_bytes



async def main():
    # temp = await get_portfolio(user_id=1994470790)
    hist_port, alltick_arr = await portfolio_into_tickerset(user_id=1994470790)
    # print(temp)
    # print(hist_port, alltick_arr)
    # print('\n')
    # print(calculate_portfolio_7d(hist_port, alltick_arr))

# if __name__ == '__main__':
#     asyncio.run(main())