import os
import requests
import pandas as pd
from tradebot.session_manager import get_api_session

BASE_URL = "https://data.definedgesecurities.com/sds/symbols"

def download_symbols(segment: str, save: bool = True) -> pd.DataFrame:
    """
    Download symbol-token mapping for given segment (e.g., NSE, NFO).
    Saves to data/symbol/{segment}_symbols.csv
    """
    folder = os.path.join("data", "symbol")
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{segment}_symbols.csv")

    session = get_api_session()
    headers = {"Authorization": session}
    url = f"{BASE_URL}/{segment}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"❌ Failed to fetch symbols: {response.text}")

    df = pd.DataFrame(response.json())

    if save:
        df.to_csv(filename, index=False)
        print(f"✅ Symbol list saved: {filename}")

    return df


def get_token(symbol: str, segment: str = "NSE") -> str:
    """
    Get token for a given symbol (from cached CSV).
    """
    filename = os.path.join("data", "symbol", f"{segment}_symbols.csv")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"⚠️ Symbol file missing: {filename}. Run download_symbols('{segment}') first.")

    df = pd.read_csv(filename)
    row = df[df["symbol"] == symbol]
    if row.empty:
        raise ValueError(f"❌ Symbol {symbol} not found in {segment} symbols.")
    return str(row.iloc[0]["token"])
