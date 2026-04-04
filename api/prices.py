"""yfinance helper — pure Python, called from api/main.jac."""

def fetch_historical_prices(ticker: str, period: str = "1y") -> list[dict]:
    import yfinance as yf
    df = yf.Ticker(ticker.upper()).history(period=period)
    if df.empty:
        return []
    prices = []
    for idx, row in df.iterrows():
        prices.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    return prices
