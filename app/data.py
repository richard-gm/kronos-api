import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone

ALPACA_DATA_BASE = "https://data.alpaca.markets/v2"


async def fetch_ohlcv(ticker: str, days: int, alpaca_key: str, alpaca_secret: str) -> pd.DataFrame:
    """Fetch daily OHLCV bars from Alpaca for the past `days` calendar days."""
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Over-fetch to account for weekends and holidays, then trim to requested length
    start = (datetime.now(timezone.utc) - timedelta(days=days + 60)).strftime("%Y-%m-%d")

    headers = {
        "APCA-API-KEY-ID": alpaca_key,
        "APCA-API-SECRET-KEY": alpaca_secret,
    }
    params = {
        "start": start,
        "end": end,
        "timeframe": "1Day",
        "adjustment": "split",
        "feed": "iex",
        "limit": 1000,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ALPACA_DATA_BASE}/stocks/{ticker}/bars",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()

    bars = resp.json().get("bars", [])
    if not bars:
        raise ValueError(f"No OHLCV data returned for {ticker}")

    df = pd.DataFrame(bars).rename(
        columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "t": "timestamp"}
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()[["open", "high", "low", "close", "volume"]]

    # Trim to exactly `days` trading days (Kronos context window)
    return df.tail(days)
