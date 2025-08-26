import os
import requests
import pandas as pd
from datetime import datetime
from tradebot.session_manager import get_api_session
from tradebot.symbol_manager import get_token

BASE_URL = "https://data.definedgesecurities.com/sds/history"

def build_url(segment: str, token: str, timeframe: str, from_date: str, to_date: str) -> str:
    """
    Build historical data API URL
    Dates must be in ddMMyyyyHHmm format
    """
    return f"{BASE_URL}/{segment}/{token}/{timeframe}/{from_date}/{to_date}"


def download_historical(symbol: str, segment: str, timeframe: str,
                        from_date: datetime, to_date: datetime, save: bool = True) -> pd.DataFrame:
    """
    Download historical data for given symbol and save in data/historical/{segment}_{symbol}_{timeframe}.csv
    - symbol: e.g. RELIANCE
    - segment: NSE / NFO etc.
    - timeframe: day / minute / tick
    - from_date, to_date: datetime objects
    """
    folder = os.path.join("data", "historical")
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{segment}_{symbol}_{timeframe}.csv")

    # Convert dates to required format ddMMyyyyHHmm
    from_str = from_date.strftime("%d%m%Y%H%M")
    to_str = to_date.strftime("%d%m%Y%H%M")

    # Token lookup
    token = get_token(symbol, segment)

    session = get_api_session()
    headers = {"Authorization": session}
    url = build_url(segment, token, timeframe, from_str, to_str)

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"❌ Failed to fetch historical data: {response.text}")

    # Convert CSV text to DataFrame
    from io import StringIO
    df = pd.read_csv(StringIO(response.text), header=None)

    # Timeframe wise column mapping
    if timeframe in ["day", "minute"]:
        df.columns = ["datetime", "open", "high", "low", "close", "volume", "oi"]
    elif timeframe == "tick":
        df.columns = ["utc", "ltp", "ltq", "oi"]

    # Avoid duplicates if file already exists
    if os.path.exists(filename):
        old_df = pd.read_csv(filename)
        df = pd.concat([old_df, df], ignore_index=True).drop_duplicates().reset_index(drop=True)

    if save:
        df.to_csv(filename, index=False)
        print(f"✅ Historical data saved: {filename}")

    return df
