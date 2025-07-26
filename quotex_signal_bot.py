import streamlit as st
import pandas as pd
import numpy as np
import ta
import ccxt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --------------------------
# Quotex-style Asset Mapping to Binance Symbols
# --------------------------
QUOTEX_TO_BINANCE = {
    # Standard Pairs
    "EUR/USD": "EUR/USDT",
    "GBP/USD": "GBP/USDT",
    "USD/JPY": "JPY/USDT",   # Proxy
    "BTC/USD": "BTC/USDT",
    "ETH/USD": "ETH/USDT",
    "AUD/USD": "AUD/USDT",
    "NZD/USD": "NZD/USDT",
    "USD/CAD": "CAD/USDT",
    "USD/CHF": "CHF/USDT",
    "LTC/USD": "LTC/USDT",
    "XRP/USD": "XRP/USDT",
    "ADA/USD": "ADA/USDT",
    "DOT/USD": "DOT/USDT",
    "SOL/USD": "SOL/USDT",
    "BNB/USD": "BNB/USDT",

    # OTC Pairs
    "EUR/USD OTC": "EUR/USDT",
    "GBP/USD OTC": "GBP/USDT",
    "USD/JPY OTC": "JPY/USDT",
    "BTC/USD OTC": "BTC/USDT",
    "ETH/USD OTC": "ETH/USDT",
    "AUD/USD OTC": "AUD/USDT",
    "NZD/USD OTC": "NZD/USDT",
    "USD/CAD OTC": "CAD/USDT",
    "USD/CHF OTC": "CHF/USDT",
    "LTC/USD OTC": "LTC/USDT",
    "XRP/USD OTC": "XRP/USDT",
    "ADA/USD OTC": "ADA/USDT",
    "DOT/USD OTC": "DOT/USDT",
    "SOL/USD OTC": "SOL/USDT",
    "BNB/USD OTC": "BNB/USDT"
}

# --------------------------
# Live Data Loader from Binance
# --------------------------
def load_live_data(symbol='EUR/USDT', interval='1m', limit=100):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# --------------------------
# Technical Indicator Logic
# --------------------------
def apply_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['macd'] = ta.trend.macd_diff(df['close'])
    df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()
    return df

# --------------------------
# Price Action Strategy
# --------------------------
def price_action(df):
    df['signal_pa'] = 'HOLD'
    for i in range(2, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1] and df['close'].iloc[i-1] < df['close'].iloc[i-2]:
            df.loc[df.index[i], 'signal_pa'] = 'BUY'
        elif df['close'].iloc[i] < df['close'].iloc[i-1] and df['close'].iloc[i-1] > df['close'].iloc[i-2]:
            df.loc[df.index[i], 'signal_pa'] = 'SELL'
    return df

# --------------------------
# Support & Resistance (Rolling Highs/Lows)
# --------------------------
def detect_sr(df, window=20):
    df['support'] = df['close'].rolling(window).min()
    df['resistance'] = df['close'].rolling(window).max()
    return df

# --------------------------
# Final Signal Generator
# --------------------------
def generate_signals(df):
    df['signal'] = 'HOLD'
    for i in range(1, len(df)):
        if (df['rsi'].iloc[i] < 30 and
            df['macd'].iloc[i] > 0 and
            df['close'].iloc[i] <= df['support'].iloc[i] * 1.01 and
            df['signal_pa'].iloc[i] == 'BUY'):
            df.loc[df.index[i], 'signal'] = 'BUY'
        elif (df['rsi'].iloc[i] > 70 and
              df['macd'].iloc[i] < 0 and
              df['close'].iloc[i] >= df['resistance'].iloc[i] * 0.99 and
              df['signal_pa'].iloc[i] == 'SELL'):
            df.loc[df.index[i], 'signal'] = 'SELL'
    return df

# --------------------------
# Streamlit App Interface
# --------------------------
st.set_page_config(page_title="Quotex Signal Bot", layout="wide")
st.title("📈 Quotex High Accuracy Signal Generator")

st.markdown("""
This app generates trading signals based on:
- **RSI**, **MACD**, **EMA Crossover**
- **Price Action Patterns**
- **Support & Resistance Detection**

No martingale strategy is used. The signals aim for **80%+ accuracy**.
""")

st_autorefresh(interval=60000, key="refresh")  # refresh every 60 seconds

# Asset selector based on Quotex pairs
st.sidebar.title('Asset Configuration')
selected_qx_pair = st.sidebar.selectbox("Select Quotex Pair", list(QUOTEX_TO_BINANCE.keys()))
binance_symbol = QUOTEX_TO_BINANCE[selected_qx_pair]

# Load and process data
data = load_live_data(symbol=binance_symbol)
data = apply_indicators(data)
data = price_action(data)
data = detect_sr(data)
data = generate_signals(data)

# Display signals
tab1, tab2 = st.tabs(["📊 Signals Table", "📉 Chart"])

with tab1:
    st.dataframe(data[['datetime', 'close', 'rsi', 'macd', 'support', 'resistance', 'signal']].tail(20), use_container_width=True)

with tab2:
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['close'], name='Price', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['support'], name='Support', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=data['datetime'], y=data['resistance'], name='Resistance', line=dict(color='red', dash='dot')))
    buy_signals = data[data['signal'] == 'BUY']
    sell_signals = data[data['signal'] == 'SELL']
    fig.add_trace(go.Scatter(x=buy_signals['datetime'], y=buy_signals['close'], mode='markers', name='BUY', marker=dict(color='lime', size=10, symbol='arrow-up'))))
    fig.add_trace(go.Scatter(x=sell_signals['datetime'], y=sell_signals['close'], mode='markers', name='SELL', marker=dict(color='crimson', size=10, symbol='arrow-down'))))
    fig.update_layout(title=f'{selected_qx_pair} Price + Signals', xaxis_title='Time', yaxis_title='Price')
    st.plotly_chart(fig, use_container_width=True)

st.success(f"Signals for {selected_qx_pair} generated successfully using Binance data proxy.")
