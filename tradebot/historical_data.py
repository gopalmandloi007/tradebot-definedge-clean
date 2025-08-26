import os
import requests
import pandas as pd
from datetime import datetime
from tradebot.session_manager import get_api_session

BASE_URL = "https://data.definedgesecurities.com/sds/history"

def get_history(
    segment: str,
    token: str,
    timeframe: str,
    from_date: str,
    to_date: str,
    save: bool = True
) -> pd.DataFrame:
    """
    Fetch historical data and save it incrementally (no duplicates).
    """

    # ✅ Folder structure
    folder = os.path.join("data", "historical", segment)
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{token}_{timeframe}.csv")

    # ✅ Agar file pehle se hai to last datetime padho
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        if timeframe in ["day", "minute"]:
            last_date = existing_df["datetime"].iloc[-1]
            # API ke format me convert (ddMMyyyyHHmm)
            last_dt = datetime.strptime(last_date, "%Y-%m-%d %H:%M:%S")
            from_date = last_dt.strftime("%d%m%Y%H%M")
        elif timeframe == "tick":
            last_utc = existing_df["utc"].iloc[-1]
            # Tick data UTC seconds hota hai → API me direct use nahi hota
            # is case me hum manually range define karenge
            # abhi ke liye user se diya hua from_date hi use hoga
    else:
        existing_df = None

    # ✅ API request
    session = get_api_session()
    headers = {"Authorization": session}
    url = f"{BASE_URL}/{segment}/{token}/{timeframe}/{from_date}/{to_date}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"❌ Failed to fetch data: {response.text}")

    # ✅ Response parse
    if timeframe in ["day", "minute"]:
        cols = ["datetime", "open", "high", "low", "close", "volume", "oi"]
    else:  # tick
        cols = ["utc", "ltp", "ltq", "oi"]

    df = pd.read_csv(pd.compat.StringIO(response.text), names=cols)

    # ✅ Agar pehle ka data tha to merge + remove duplicates
    if existing_df is not None:
        df = pd.concat([existing_df, df])
        df.drop_duplicates(subset=cols[0], keep="last", inplace=True)
        df.reset_index(drop=True, inplace=True)

    # ✅ Save
    if save:
        df.to_csv(filename, index=False)
        print(f"✅ Data saved: {filename}")

    return df
