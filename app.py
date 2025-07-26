
import requests
import pandas as pd
import ta
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Quotex Signal Bot (High Accuracy)", layout="centered")
st.title("📈 Quotex High Accuracy Signal Generator (No Martingale)")

symbol = st.text_input("Enter Symbol (e.g. BTCUSDT, ETHUSDT)", "BTCUSDT")

BINANCE_ENDPOINT = "https://api.binance.com/api/v3/klines"

if st.button("Generate Signal"):
    try:
        params = {
            "symbol": symbol.upper(),
            "interval": "1m",
            "limit": 60
        }
        response = requests.get(BINANCE_ENDPOINT, params=params)
        data = response.json()

        if len(data) < 60:
            st.warning("Not enough data received from Binance. Try again later.")
            st.stop()

        df = pd.DataFrame(data, columns=[
            "OpenTime", "Open", "High", "Low", "Close", "Volume",
            "CloseTime", "QuoteAssetVolume", "NumberOfTrades",
            "TakerBuyBaseAssetVolume", "TakerBuyQuoteAssetVolume", "Ignore"])

        df["Open"] = df["Open"].astype(float)
        df["Close"] = df["Close"].astype(float)
        df["High"] = df["High"].astype(float)
        df["Low"] = df["Low"].astype(float)

        # Indicators
        df['rsi'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['ema_20'] = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator()
        df['stoch_rsi'] = ta.momentum.StochRSIIndicator(df['Close']).stochrsi_k()

        recent_high = df['High'][-10:].max()
        recent_low = df['Low'][-10:].min()

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        # Candlestick patterns
        is_bullish_engulfing = previous['Close'] < previous['Open'] and latest['Close'] > latest['Open'] and latest['Close'] > previous['Open'] and latest['Open'] < previous['Close']
        is_bearish_engulfing = previous['Close'] > previous['Open'] and latest['Close'] < latest['Open'] and latest['Close'] < previous['Open'] and latest['Open'] > previous['Close']

        body = abs(latest['Close'] - latest['Open'])
        range_ = latest['High'] - latest['Low']
        is_doji = body / range_ < 0.1
        is_hammer = (latest['High'] - max(latest['Close'], latest['Open']) < range_ * 0.2) and ((min(latest['Close'], latest['Open']) - latest['Low']) > range_ * 0.5)
        is_morning_star = (
            df.iloc[-3]['Close'] < df.iloc[-3]['Open'] and
            abs(df.iloc[-2]['Close'] - df.iloc[-2]['Open']) / (df.iloc[-2]['High'] - df.iloc[-2]['Low']) < 0.3 and
            df.iloc[-1]['Close'] > df.iloc[-1]['Open'] and
            df.iloc[-1]['Close'] > (df.iloc[-3]['Open'] + df.iloc[-3]['Close']) / 2
        )

        # Signal logic
        buy_conditions = (
            latest['rsi'] < 30 and
            latest['macd'] > latest['macd_signal'] and
            latest['Close'] > latest['ema_20'] > latest['ema_50'] and
            latest['stoch_rsi'] < 0.2 and
            latest['Close'] > recent_low and
            (is_bullish_engulfing or is_hammer or is_morning_star)
        )

        sell_conditions = (
            latest['rsi'] > 70 and
            latest['macd'] < latest['macd_signal'] and
            latest['Close'] < latest['ema_20'] < latest['ema_50'] and
            latest['stoch_rsi'] > 0.8 and
            latest['Close'] < recent_high and
            (is_bearish_engulfing or is_doji)
        )

        if buy_conditions:
            signal = "🔼 STRONG BUY Signal"
        elif sell_conditions:
            signal = "🔽 STRONG SELL Signal"
        else:
            signal = "🟨 No Clear Signal (Wait)"

        st.success(f"[{datetime.now().strftime('%H:%M:%S')}]")
        st.info(f"Symbol: {symbol}\nPrice: {latest['Close']:.5f}\nSignal: {signal}\nSupport: {recent_low:.2f}\nResistance: {recent_high:.2f}")

        st.write("### Price Action Flags:")
        st.write(f"- Bullish Engulfing: {is_bullish_engulfing}")
        st.write(f"- Bearish Engulfing: {is_bearish_engulfing}")
        st.write(f"- Doji: {is_doji}")
        st.write(f"- Hammer: {is_hammer}")
        st.write(f"- Morning Star: {is_morning_star}")

    except Exception as e:
        st.error(f"Error: {e}")
