# src/pages/tradebook.py
import streamlit as st
from tradebot.api_client import APIClient
from tradebot.book_manager import BookManager
import pandas as pd

st.set_page_config(page_title="Trade Book", layout="wide")
st.title("🧾 Trade Book")

api = APIClient()
bm = BookManager(api)

if st.button("🔄 Refresh Trades"):
    st.experimental_rerun()

trades = bm.get_trade_book()
if not trades:
    st.warning("No trades found.")
else:
    df = pd.json_normalize(trades)
    # choose columns to show if present
    display_cols = ["fill_id","order_id","exchange","tradingsymbol","filled_qty","fill_price","fill_time","exchange_orderid"]
    cols_present = [c for c in display_cols if c in df.columns]
    st.dataframe(df[cols_present].sort_values("fill_time", ascending=False).reset_index(drop=True))

    # download CSV
    csv = df.to_csv(index=False)
    st.download_button("⬇️ Download Trades CSV", csv, file_name="tradebook.csv", mime="text/csv")
