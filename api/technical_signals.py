"""Compute technical signals for a ticker using yfinance + pandas.

Called from _jac_worker_main.py before the Jac pipeline runs, so quant
walkers receive real computed numbers rather than relying on LLM knowledge.
"""

import logging

logger = logging.getLogger("api.technical_signals")


def compute_signals(ticker: str) -> dict:
    import yfinance as yf

    df = yf.Ticker(ticker.upper()).history(period="1y")
    if df.empty or len(df) < 30:
        return {}

    close = df["Close"]

    # RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi_14 = round(float(rsi_series.iloc[-1]), 1)

    # Moving averages
    ma50_series = close.rolling(50).mean()
    ma200_series = close.rolling(200).mean()
    price = round(float(close.iloc[-1]), 2)
    ma50 = round(float(ma50_series.iloc[-1]), 2) if len(close) >= 50 else None
    ma200 = round(float(ma200_series.iloc[-1]), 2) if len(close) >= 200 else None

    # MA crossover signal
    if ma50 is not None and ma200 is not None and len(close) >= 201:
        ma50_prev = float(ma50_series.iloc[-2])
        ma200_prev = float(ma200_series.iloc[-2])
        if ma50 > ma200 and ma50_prev <= ma200_prev:
            ma_cross = "golden cross (recent)"
        elif ma50 < ma200 and ma50_prev >= ma200_prev:
            ma_cross = "death cross (recent)"
        elif ma50 > ma200:
            ma_cross = "50-day above 200-day (bullish alignment)"
        else:
            ma_cross = "50-day below 200-day (bearish alignment)"
    elif ma50 is not None:
        ma_cross = "above 50-day MA" if price > ma50 else "below 50-day MA"
    else:
        ma_cross = "insufficient history"

    # Realized volatility (30-day annualized)
    returns = close.pct_change().dropna()
    realized_vol = round(float(returns.tail(30).std() * (252 ** 0.5) * 100), 1)

    # Price momentum
    def safe_mom(n):
        if len(close) > n:
            return round((float(close.iloc[-1]) / float(close.iloc[-n]) - 1) * 100, 1)
        return None

    return {
        "price": price,
        "rsi_14": rsi_14,
        "ma50": ma50,
        "ma200": ma200,
        "ma_cross": ma_cross,
        "realized_vol_30d": realized_vol,
        "mom_1m": safe_mom(21),
        "mom_3m": safe_mom(63),
        "mom_6m": safe_mom(126),
    }


def format_signals_for_prompt(ticker: str, signals: dict) -> str:
    if not signals:
        return f"[No technical signal data available for {ticker}]"

    rsi = signals["rsi_14"]
    rsi_label = "OVERBOUGHT" if rsi > 70 else ("OVERSOLD" if rsi < 30 else "neutral")

    lines = [
        f"COMPUTED TECHNICAL SIGNALS FOR {ticker} (use these as your factual foundation):",
        f"  Current Price: ${signals['price']}",
        f"  RSI (14-day): {rsi} [{rsi_label}]",
    ]
    if signals["ma50"]:
        ma200_str = f"${signals['ma200']}" if signals["ma200"] else "N/A (< 200 days data)"
        lines.append(f"  50-day MA: ${signals['ma50']}  |  200-day MA: {ma200_str}")
    lines.append(f"  MA Signal: {signals['ma_cross']}")
    lines.append(f"  Realized Volatility (30d annualized): {signals['realized_vol_30d']}%")

    mom_parts = []
    if signals["mom_1m"] is not None:
        mom_parts.append(f"1-month {signals['mom_1m']:+.1f}%")
    if signals["mom_3m"] is not None:
        mom_parts.append(f"3-month {signals['mom_3m']:+.1f}%")
    if signals["mom_6m"] is not None:
        mom_parts.append(f"6-month {signals['mom_6m']:+.1f}%")
    if mom_parts:
        lines.append(f"  Price Return: {', '.join(mom_parts)}")

    return "\n".join(lines)


def compute_signals_safe(ticker: str) -> str:
    """Returns formatted signal string, or empty string on any failure."""
    try:
        signals = compute_signals(ticker)
        return format_signals_for_prompt(ticker, signals)
    except Exception as exc:
        logger.warning("Signal computation failed for %s: %s", ticker, exc)
        return ""
