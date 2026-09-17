import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import seaborn as sns

def hm(*tickers):
    ms = []
    for x in tickers:
        ms.append(x)

    data = yf.download(ms, period='2y', auto_adjust=True)['Close']
    rets = data.pct_change()

    mtx = rets.corr()

    plt.imshow(mtx, cmap='hot', interpolation='nearest')
    plt.colorbar()
    plt.show()

    return mtx

# hm("AAPL", "MSFT", "TSLA", "^GSPC")

def SMA_EMA_no_zachemto_2(ticker1: str, ticker2: str):
    dw1 = yf.download(ticker1, period="1y", progress=False, threads=False)['Close']
    dw2 = yf.download(ticker2, period="1y", progress=False, threads=False)['Close']

    df1 = pd.DataFrame(dw1)
    df2 = pd.DataFrame(dw2)

    res = pd.merge(df1, df2, on="Date")
    
    res["SMA_20"] = res[f"{ticker1}"].rolling(window=20).mean()
    res['EMA_20'] = res[f"{ticker1}"].ewm(span=20, adjust=False).mean()

    print(res["SMA_20"])

    plt.figure(figsize=(10,5))
    plt.plot(res[f'{ticker1}'], label=f'Цена закрытия {ticker1}', color='blue', alpha=0.5)
    plt.plot(res['SMA_20'], label='SMA 20', color='green')
    plt.title('SMA в Python')
    plt.legend()
    plt.show()

def SMA_EMA_GRAPH(ticker1: str):
    dw1 = yf.download(ticker1, period="1y", progress=False, threads=False)['Close']

    res = pd.DataFrame(dw1)
    
    res["SMA_20"] = res[f"{ticker1}"].rolling(window=20).mean()
    res['EMA_20'] = res[f"{ticker1}"].ewm(span=20, adjust=False).mean()

    print(res["SMA_20"])

    plt.figure(figsize=(10,5))
    plt.plot(res[f'{ticker1}'], label=f'Цена закрытия {ticker1}', color='blue', alpha=0.5)
    plt.plot(res['SMA_20'], label='SMA 20', color='green')
    plt.plot(res['EMA_20'], label='EMA 20', color='red')
    plt.title(f'SMA and EMA for {ticker1}')
    plt.legend()
    plt.show()

# SMA_EMA_GRAPH("AAPL")

def RSI_GRAPH(ticker: str, n: int=14):
    dw1 = yf.download(ticker, period="1y", progress=False, threads=False)['Close']
    data = pd.DataFrame(dw1)
    delta = data.diff()

    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    avg_gain = gain.ewm(com=n-1, adjust=False).mean()
    avg_loss = loss.ewm(com=n-1, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    data[f"RSI_{n}"] = rsi[f"{ticker}"]

    plt.figure(figsize=(10,5))
    plt.plot(data[f'RSI_{n}'], label= f'RSI_{n}', color='green')

    plt.axhline(70, color='red', linestyle='--', alpha=0.5, label='Overbought (70)')
    plt.axhline(30, color='blue', linestyle='--', alpha=0.5, label='Oversold (30)')
    plt.fill_between(rsi.index, 30, 70, color='gray', alpha=0.1)

    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)
    plt.title(f'RSI for {ticker}')
    plt.legend()
    plt.show()

    return rsi

# print(RSI_GRAPH("AAPL", 14))



def calculate_macd_GRAPH(ticker, fast=12, slow=26, signal=9):
    dw1 = yf.download(ticker, period="1y", progress=False, threads=False)['Close']
    data = pd.DataFrame(dw1)

    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()

    data['MACD'] = ema_fast - ema_slow

    data['Signal'] = data['MACD'].ewm(span=signal, adjust=False).mean()
    
    data['Histogram'] = data['MACD'] - data['Signal']



    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, 
                                   gridspec_kw={'height_ratios': [2, 1]})

    # --- Верхний график: Цена ---
    ax1.plot(data.index, data[f'{ticker}'], label='Price', color='black', alpha=0.7)
    ax1.set_title(f"MACD Indicator for {ticker}")
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # --- Нижний график: MACD ---
    # Линии MACD и Signal
    ax2.plot(data.index, data['MACD'], label='MACD', color='blue', lw=1.5)
    ax2.plot(data.index, data['Signal'], label='Signal', color='red', lw=1.5)
    
    # Гистограмма (зеленая если выше 0, красная если ниже)
    colors = ['green' if x > 0 else 'red' for x in data['Histogram']]
    ax2.bar(data.index, data['Histogram'], label='Histogram', color=colors, alpha=0.5)

    ax2.axhline(0, color='black', lw=1, ls='--') # Нулевая линия
    ax2.set_ylabel('Value')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()



    return data

# print(calculate_macd_GRAPH("AAPL"))



def get_bollinger_bands_GRAPH(prices, window=20, num_std=2):
    # Рассчитываем скользящее среднее (Middle Band)
    rolling_mean = prices.rolling(window=window).mean()
    
    # Рассчитываем скользящее стандартное отклонение
    rolling_std = prices.rolling(window=window).std()
    
    # Рассчитываем верхнюю и нижнюю границы
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    
    return upper_band, rolling_mean, lower_band

# print(get_bollinger_bands_GRAPH(pd.DataFrame(yf.download("AAPL", period="1y", progress=False, threads=False)['Close'])))



def bollbands_GRAPH(ticker, window=20, k=2):
    dw1 = yf.download(ticker, period="1y", progress=False, threads=False)['Close']
    data = pd.DataFrame(dw1)

    data['rolling_mean'] = data[f'{ticker}'].rolling(window=window).mean()
    data['rolling_std'] = data[f'{ticker}'].rolling(window=window).std()

    data['upper_band'] = data['rolling_mean'] + (data['rolling_std'] * k)
    data['lower_band'] = data['rolling_mean'] - (data['rolling_std'] * k)

    plt.figure(figsize=(12, 6))

    # Основная цена
    plt.plot(data.index, data[ticker], label='Price', color='black', lw=1.5, alpha=0.8)
    
    # Линии полос
    plt.plot(data.index, data["upper_band"], color='blue', lw=1, alpha=0.3, label='Bollinger Bands')
    plt.plot(data.index, data["lower_band"], color='blue', lw=1, alpha=0.3)
    
    # Средняя линия (часто делают пунктиром)
    plt.plot(data.index, data["rolling_mean"], color='orange', lw=1, ls='--', alpha=0.7, label='Moving Average')

    # Заполнение пространства между полосами
    plt.fill_between(data.index, data["lower_band"], data["upper_band"], color='green', alpha=0.1)

    plt.title(f'Bollinger Bands for {ticker}')
    plt.legend(loc='best')
    plt.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.show()

    return data

# print(bollbands_GRAPH("AAPL"))




def ATR_GRAPH(ticker, window=14, period="1y"):
    df = yf.download(
        ticker, 
        period=period, 
        multi_level_index=False   # ← вот это главное
    )
    
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    data = pd.DataFrame({
        'Close': df['Close'],
        'TR': tr,
        'ATR': atr
    })

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), 
                                   sharex=True, 
                                   gridspec_kw={'height_ratios': [3, 1]})
    
    # Верхний график — цена
    ax1.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=2)
    ax1.set_title(f'{ticker} — Price and ATR({window})')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Нижний график — ATR
    ax2.plot(data.index, data['ATR'], label=f'ATR({window})', color='orange', linewidth=2)
    ax2.set_ylabel('ATR')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.xlabel('Date')
    plt.tight_layout()
    plt.show()

    return data

# print(ATR_GRAPH("AAPL"))




#Тут уже функции на проверку алертами
def get_data_df(ticker: str, period: str = "60d", interval: str = "1d", **kwargs):
    """
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y...
    interval: 1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk...
    """
    data = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        threads=False,
        auto_adjust=True,
        multi_level_index=False,  # Отключает мультииндекс для одиночного тикера
        **kwargs
    )
    return data

def add_sma_ema(df: pd.DataFrame, fast: int = 9, slow: int = 21, signal: int = 5):
    close = df['Close']
    df['SMA_fast'] = close.rolling(window=fast).mean()
    df['SMA_slow'] = close.rolling(window=slow).mean()
    df['EMA_fast'] = close.ewm(span=fast, adjust=False).mean()
    df['EMA_slow'] = close.ewm(span=slow, adjust=False).mean()
    return df

def check_ma_crossover(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = {
        "golden_cross": (prev['SMA_fast'] < prev['SMA_slow'] and 
                         latest['SMA_fast'] > latest['SMA_slow']),
        "death_cross": (prev['SMA_fast'] > prev['SMA_slow'] and 
                       latest['SMA_fast'] < latest['SMA_slow']),
        "price_above_ema": latest['Close'] > latest['EMA_fast'],
        # можно добавить EMA_fast > EMA_slow и т.д.
    }
    return signals

def add_rsi(df: pd.DataFrame, period: int = 14):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def check_rsi(df: pd.DataFrame, overbought=70, oversold=30):
    latest = df.iloc[-1]['RSI']
    prev = df.iloc[-2]['RSI']
    
    return {
        "overbought": latest > overbought,
        "oversold": latest < oversold,
        "crossing_up_30": prev <= 30 and latest > 30,
        "crossing_down_70": prev >= 70 and latest < 70,
        "value": round(latest, 2)
    }

def add_macd(df: pd.DataFrame, fast=12, slow=26, signal=9):
    close = df['Close']
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    df['MACD'] = ema_fast - ema_slow
    df['Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    return df

def check_macd(df: pd.DataFrame):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    return {
        "bullish_crossover": (prev['MACD'] < prev['Signal'] and 
                             latest['MACD'] > latest['Signal']),
        "bearish_crossover": (prev['MACD'] > prev['Signal'] and 
                             latest['MACD'] < latest['Signal']),
        "histogram_positive": latest['Histogram'] > 0,
        "histogram_expanding": abs(latest['Histogram']) > abs(prev['Histogram'])
    }

def add_bollinger(df: pd.DataFrame, window=20, k=2):
    close = df['Close']
    df['BB_middle'] = close.rolling(window=window).mean()
    df['BB_std'] = close.rolling(window=window).std()
    df['BB_upper'] = df['BB_middle'] + k * df['BB_std']
    df['BB_lower'] = df['BB_middle'] - k * df['BB_std']
    df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']

    return df

def check_bollinger(df: pd.DataFrame):
    latest = df.iloc[-1]
    return {
        "price_above_upper": latest['Close'] > latest['BB_upper'],
        "price_below_lower": latest['Close'] < latest['BB_lower'],
        "squeeze": latest['BB_width'] < df['BB_width'].quantile(0.2),  # сжатие
    }

def add_atr(df: pd.DataFrame, window=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    return df

def get_current_rsi(ticker: str, period: int = 14, **kwargs) -> float | None:
    df = get_data_df(ticker, **kwargs)          # или get_data_df(ticker, interval="5m", period="5d")
    if df is None or len(df) < 14:
        return None
    series = add_rsi(df, period=period)              
    return series['RSI'].iloc[-1]         

def get_current_macd(ticker: str, fast: int = 12, slow: int = 26, signal: int = 9, **kwargs) -> float | None:
    df = get_data_df(ticker, **kwargs)
    macd_df = add_macd(df, fast=fast, slow=slow, signal=signal) 
    macd_series = macd_df['MACD']
    return macd_series.iloc[-1] if macd_series is not None else None
#ДОДЕЛАТЬ ПОТОМ ДОБАВИТЬ ДРУГИЕ СТОЛБЦЫ MACD

def get_current_bollinger_upper(ticker: str, bb_period: int = 20, **kwargs) -> float | None:
    df = get_data_df(ticker, **kwargs)
    df_bb = add_bollinger(df, window=bb_period)
    upper_band_series = df_bb['BB_upper']
    return upper_band_series.iloc[-1]



def get_current_bollinger_lower(ticker: str, bb_period: int = 20, **kwargs) -> float | None:
    df = get_data_df(ticker, **kwargs)
    df_bb = add_bollinger(df, window=bb_period)
    upper_band_series = df_bb['BB_lower']
    return upper_band_series.iloc[-1]

def get_current_atr(ticker: str, atr_period: int = 14, **kwargs) -> float | None:
    df = get_data_df(ticker, **kwargs)

    if df is None or df.empty or len(df) < atr_period:
        return None

    df_atr = add_atr(df, window=atr_period)
    atr_series = df_atr['ATR']
    return atr_series.iloc[-1]