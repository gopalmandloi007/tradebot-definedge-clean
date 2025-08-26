"""
historical_data.py

Responsibilities:
- Download historical data from Definedge:
  https://data.definedgesecurities.com/sds/history/{segment}/{token}/{timeframe}/{from}/{to}
- Parse CSV (no headers) into pandas DataFrame for 'day', 'minute', 'tick'
- Save files under data/historical/{segment}/{token}_{timeframe}.csv
- Auto-append: if file exists, only fetch the missing tail (based on last timestamp)
- Provide helper get_previous_close(exchange, token, timeframe="day")
"""

from __future__ import annotations
import os
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import requests
from io import StringIO

HISTORY_BASE = "https://data.definedgesecurities.com/sds/history"
DATA_DIR = os.path.join("data", "historical")


class HistoricalDataError(Exception):
    pass


class HistoricalDataManager:
    def __init__(self, api_client):
        """
        api_client: should expose either:
          - .get(path_or_full_url, params=None) returning requests.Response-like or parsed text,
          - OR have method get_auth_headers() to produce {"Authorization": "..."}
        We will try to use api_client.get(full_url) first; if not available fallback to requests.get with headers from api_client.get_auth_headers()
        """
        self.api_client = api_client
        os.makedirs(DATA_DIR, exist_ok=True)

    # ---------------- utilities ----------------
    @staticmethod
    def _fmt_dt_for_api(dt: datetime) -> str:
        # ddMMyyyyHHmm
        return dt.strftime("%d%m%Y%H%M")

    @staticmethod
    def _parse_day_minute_df(text: str) -> pd.DataFrame:
        """
        CSV for day/minute: Dateandtime, Open, High, Low, Close, Volume, Open Interest (OI only for derivatives)
        Dateandtime format likely: 'YYYY-MM-DD HH:MM:SS' or something similar; we will parse flexibly.
        """
        cols = ["datetime", "open", "high", "low", "close", "volume", "oi"]
        df = pd.read_csv(StringIO(text), names=cols, header=None, low_memory=False)
        # Try to parse datetime column robustly
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        return df

    @staticmethod
    def _parse_tick_df(text: str) -> pd.DataFrame:
        """
        CSV for tick: UTC(in seconds), LTP, LTQ, OI
        """
        cols = ["utc", "ltp", "ltq", "oi"]
        df = pd.read_csv(StringIO(text), names=cols, header=None, low_memory=False)
        # Convert UTC seconds to datetime for convenience (UTC)
        try:
            df["utc"] = pd.to_datetime(df["utc"].astype(float), unit="s", errors="coerce")
        except Exception:
            df["utc"] = pd.to_datetime(df["utc"], errors="coerce")
        return df

    def _local_filename(self, segment: str, token: str, timeframe: str) -> str:
        folder = os.path.join(DATA_DIR, segment)
        os.makedirs(folder, exist_ok=True)
        # token may be int or string; normalize to str
        return os.path.join(folder, f"{token}_{timeframe}.csv")

    def _last_timestamp_in_file(self, filepath: str, timeframe: str) -> Optional[datetime]:
        if not os.path.exists(filepath):
            return None
        try:
            df = pd.read_csv(filepath, parse_dates=["datetime"] if timeframe in ("day", "minute") else [], low_memory=False)
        except Exception:
            # fallback without parse
            df = pd.read_csv(filepath, low_memory=False)

        if df.empty:
            return None

        if timeframe in ("day", "minute"):
            if "datetime" in df.columns:
                last = pd.to_datetime(df["datetime"].iloc[-1], errors="coerce")
                return pd.Timestamp(last).to_pydatetime() if not pd.isna(last) else None
        elif timeframe == "tick":
            # ticks saved with utc datetime column name 'utc' if our parser used that
            if "utc" in df.columns:
                last = pd.to_datetime(df["utc"].iloc[-1], errors="coerce")
                return pd.Timestamp(last).to_pydatetime() if not pd.isna(last) else None
        return None

    def _call_history_api(self, segment: str, token: str, timeframe: str, from_dt: datetime, to_dt: datetime) -> str:
        """
        Call the external historical URL and return response text.
        We first try api_client.get(full_url) if available and returns text; otherwise fallback to requests.get with auth header.
        """
        from_str = self._fmt_dt_for_api(from_dt)
        to_str = self._fmt_dt_for_api(to_dt)
        full_url = f"{HISTORY_BASE}/{segment}/{token}/{timeframe}/{from_str}/{to_str}"

        # Try api_client.get(full_url)
        try:
            # If api_client has 'get' we call it and try to read .text
            resp = self.api_client.get(full_url)
            # If api_client.get returned requests.Response-like
            if hasattr(resp, "status_code"):
                if resp.status_code != 200:
                    raise HistoricalDataError(f"History API returned {resp.status_code}: {getattr(resp, 'text', '')}")
                return resp.text
            # If returned a dict/string directly
            if isinstance(resp, str):
                return resp
            # If returned parsed JSON (unlikely for history as it's CSV), attempt to stringify
            return str(resp)
        except Exception:
            # Fallback: use requests with headers from api_client if possible
            headers = {}
            try:
                if hasattr(self.api_client, "get_auth_headers"):
                    headers.update(self.api_client.get_auth_headers())
                elif hasattr(self.api_client, "session_manager") and hasattr(self.api_client.session_manager, "get_auth_headers"):
                    headers.update(self.api_client.session_manager.get_auth_headers())
            except Exception:
                pass

            r = requests.get(full_url, headers=headers, timeout=30)
            if r.status_code != 200:
                raise HistoricalDataError(f"History API failed: {r.status_code} {r.text}")
            return r.text

    # --------------- Public methods -----------------
    def download(self, segment: str, token: str, timeframe: str, from_dt: datetime, to_dt: datetime, save: bool = True) -> pd.DataFrame:
        """
        Download historical data for the requested range and auto-append to local file.
        - segment: NSE/BSE/NFO/CDS/MCX
        - token: instrument token (string or int)
        - timeframe: 'day' | 'minute' | 'tick'
        - from_dt, to_dt: datetime objects
        - save: whether to persist locally (default True)

        Returns: pandas.DataFrame of the combined (existing + new) data (or just new data if no local file)
        """
        token_str = str(token)
        local_file = self._local_filename(segment, token_str, timeframe)

        # If local file exists, compute from_dt based on last saved timestamp
        last_ts = self._last_timestamp_in_file(local_file, timeframe)
        if last_ts is not None:
            # Advance from_dt to next unit to avoid duplicate row
            if timeframe == "day":
                new_from = last_ts + timedelta(days=1)
            elif timeframe == "minute":
                new_from = last_ts + timedelta(minutes=1)
            else:  # tick
                # For tick we will request last 1 day to be safe (cannot easily do +1 second safely)
                new_from = last_ts + timedelta(seconds=1)
            # If new_from is after requested to_dt, nothing to download
            if new_from >= to_dt:
                # Nothing new to fetch
                # Return existing file as DataFrame
                existing_df = pd.read_csv(local_file, parse_dates=["datetime"] if timeframe in ("day", "minute") else [], low_memory=False)
                return existing_df
            # Replace from_dt for API call
            from_dt_api = new_from
        else:
            from_dt_api = from_dt

        # Call API
        text = self._call_history_api(segment, token_str, timeframe, from_dt_api, to_dt)

        # Parse response
        if timeframe in ("day", "minute"):
            new_df = self._parse_day_minute_df(text)
        else:
            new_df = self._parse_tick_df(text)

        # If local exists -> merge with existing and dedupe
        if os.path.exists(local_file):
            try:
                if timeframe in ("day", "minute"):
                    existing_df = pd.read_csv(local_file, parse_dates=["datetime"], low_memory=False)
                else:
                    existing_df = pd.read_csv(local_file, parse_dates=["utc"], low_memory=False)
            except Exception:
                existing_df = pd.read_csv(local_file, low_memory=False)

            # concat, drop duplicates based on timestamp column
            if timeframe in ("day", "minute"):
                combined = pd.concat([existing_df, new_df], ignore_index=True)
                # drop duplicates by 'datetime' (keeping last)
                combined["datetime"] = pd.to_datetime(combined["datetime"], errors="coerce")
                combined.sort_values("datetime", inplace=True)
                combined.drop_duplicates(subset=["datetime"], keep="last", inplace=True)
            else:
                combined = pd.concat([existing_df, new_df], ignore_index=True)
                combined["utc"] = pd.to_datetime(combined["utc"], errors="coerce")
                combined.sort_values("utc", inplace=True)
                combined.drop_duplicates(subset=["utc"], keep="last", inplace=True)

            combined.reset_index(drop=True, inplace=True)
            result_df = combined
        else:
            # no existing -> new_df becomes result
            result_df = new_df

        # Save if requested
        if save:
            # Ensure consistent datetime formatting for day/minute
            if timeframe in ("day", "minute") and "datetime" in result_df.columns:
                # store ISO format as string
                result_df["datetime"] = pd.to_datetime(result_df["datetime"], errors="coerce")
            elif timeframe == "tick" and "utc" in result_df.columns:
                result_df["utc"] = pd.to_datetime(result_df["utc"], errors="coerce")

            # write CSV (index False)
            result_df.to_csv(local_file, index=False)
            # Inform
            print(f"✅ Saved historical file: {local_file}")

        return result_df

    def get_previous_close(self, segment: str, token: str, timeframe: str = "day") -> Optional[float]:
        """
        Return the previous completed close price (not a live candle).
        Strategy:
          - Use local stored file if available. Take the last *complete* row (for 'day' it's last row,
            but if today is still trading day, we take previous row).
          - If local not available, attempt to download last 7 days to ensure we have previous close.
        """
        token_str = str(token)
        local_file = self._local_filename(segment, token_str, timeframe)

        if os.path.exists(local_file):
            try:
                if timeframe in ("day", "minute"):
                    df = pd.read_csv(local_file, parse_dates=["datetime"], low_memory=False)
                    if df.empty or len(df) == 0:
                        return None
                    # If last row's datetime is today (partial), we pick second last
                    last_dt = pd.to_datetime(df["datetime"].iloc[-1], errors="coerce")
                    now = pd.Timestamp.utcnow().tz_localize(None)
                    # If the last timestamp's date is today's date -> pick previous row if available
                    if last_dt.date() == now.date() and len(df) >= 2:
                        prev_close = df["close"].iloc[-2]
                    else:
                        prev_close = df["close"].iloc[-1]
                    try:
                        return float(prev_close)
                    except Exception:
                        return None
                else:
                    # For tick timeframe, previous close concept not directly applicable
                    return None
            except Exception:
                pass

        # Fallback: attempt to download last 7 days of day data and then compute
        try:
            to_dt = datetime.utcnow()
            from_dt = to_dt - timedelta(days=10)
            df = self.download(segment, token_str, "day", from_dt, to_dt, save=True)
            if df is None or df.empty:
                return None
            # After download, compute same as above
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
            if len(df) >= 2:
                # last may be today partial — pick second last
                last_dt = df["datetime"].iloc[-1]
                now = pd.Timestamp.utcnow().tz_localize(None)
                if last_dt.date() == now.date() and len(df) >= 2:
                    prev_close = df["close"].iloc[-2]
                else:
                    prev_close = df["close"].iloc[-1]
                try:
                    return float(prev_close)
                except Exception:
                    return None
        except Exception:
            return None

        return None
