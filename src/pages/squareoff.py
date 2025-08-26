# src/pages/squareoff.py
import streamlit as st
from tradebot.api_client import APIClient
from tradebot.positions_manager import PositionsManager
import pandas as pd

st.set_page_config(page_title="Square Off", layout="wide")
st.title("⚔️ Square Off Positions")

api = APIClient()
pm = PositionsManager(api)

if st.button("🔄 Refresh Positions"):
    st.experimental_rerun()

positions = pm.get_positions()
if not positions:
    st.info("No open positions today.")
else:
    df = pd.json_normalize(positions)
    # show relevant columns
    cols = ["exchange","tradingsymbol","net_quantity","net_averageprice","unrealized_pnl"]
    existing = [c for c in cols if c in df.columns]
    st.dataframe(df[existing].reset_index(drop=True))

    # Square off per position
    st.markdown("### Square off single position")
    choices = df["tradingsymbol"].tolist()
    sel = st.selectbox("Select position", options=["--select--"] + choices)
    if sel and sel != "--select--":
        row = df[df["tradingsymbol"] == sel].iloc[0]
        net_qty = int(float(row.get("net_quantity", 0)))
        st.write(f"Net quantity: {net_qty}")
        qty_to_close = st.number_input("Quantity to square off", min_value=1, max_value=abs(net_qty), value=abs(net_qty))
        if st.button("Square Off"):
            # Implement squareoff via placeorder with variety SQUAREOFF or dedicated endpoint
            payload = {
                "exchange": row.get("exchange"),
                "tradingsymbol": sel,
                "order_type": "SELL" if net_qty > 0 else "BUY",
                "quantity": str(int(qty_to_close)),
                "price_type": "MARKET",
                "product_type": "INTRADAY",
                "variety": "SQUAREOFF",
                "price": "0"
            }
            try:
                resp = api.post("/placeorder", json=payload)
                st.success(f"Squareoff response: {resp}")
            except Exception as e:
                st.error(f"Squareoff failed: {e}")
