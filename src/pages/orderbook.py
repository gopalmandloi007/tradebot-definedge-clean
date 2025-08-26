# src/pages/orderbook.py
import streamlit as st
from tradebot.api_client import APIClient
from tradebot.book_manager import BookManager
import pandas as pd
import time

st.set_page_config(page_title="Order Book", layout="wide")
st.title("📋 Order Book")

# --- init clients (SessionManager should have been logged-in and APIClient configured) ---
api = APIClient()            # expects session_manager inside or auth set in APIClient
bm = BookManager(api)

# refresh control
if "order_refresh" not in st.session_state:
    st.session_state["order_refresh"] = 0

col1, col2 = st.columns([1,4])
with col1:
    if st.button("🔄 Refresh Orders"):
        st.session_state["order_refresh"] += 1
        time.sleep(0.2)

with col2:
    st.info("Order Book shows today's orders. You can Cancel / Modify (open orders).")

# Fetch orders
orders = bm.get_order_book()

if not orders:
    st.warning("No orders returned (or API failed).")
else:
    # normalize to DataFrame for display
    df = pd.json_normalize(orders)
    # show relevant columns
    display_cols = ["order_id","exchange","tradingsymbol","quantity","filled_qty",
                    "pending_qty","price_type","price","order_status","order_type","variety","order_entry_time"]
    cols_present = [c for c in display_cols if c in df.columns]
    st.dataframe(df[cols_present].sort_values("order_entry_time", ascending=False).reset_index(drop=True))

    # action: select order to Cancel / Modify
    st.markdown("### Manage an order")
    order_ids = df["order_id"].astype(str).tolist()
    selected_order_id = st.selectbox("Select Order ID", options=["--select--"] + order_ids)
    if selected_order_id and selected_order_id != "--select--":
        row = df[df["order_id"].astype(str) == selected_order_id].iloc[0].to_dict()
        st.write("Selected order details:")
        st.json(row)

        colc, colm = st.columns(2)
        with colc:
            if st.button("❌ Cancel Order"):
                if st.confirm := st.button: pass
                try:
                    resp = api.get(f"/cancel/{selected_order_id}")
                    st.success(f"Cancel response: {resp}")
                    st.session_state["order_refresh"] += 1
                except Exception as e:
                    st.error(f"Cancel failed: {e}")

        with colm:
            st.markdown("**Modify Order**")
            # prefill modify form with current values (if present)
            new_price = st.number_input("New Price", value=float(row.get("price", 0.0)), step=0.05)
            new_qty = st.number_input("New Quantity", value=int(float(row.get("quantity", 0))), step=1)
            if st.button("✏️ Submit Modify"):
                payload = {
                    "exchange": row.get("exchange"),
                    "order_id": selected_order_id,
                    "tradingsymbol": row.get("tradingsymbol"),
                    "quantity": str(int(new_qty)),
                    "price": str(new_price),
                    "product_type": row.get("product_type", "NORMAL"),
                    "order_type": row.get("order_type"),
                    "price_type": row.get("price_type", "LIMIT"),
                    "validity": row.get("validity", "DAY")
                }
                try:
                    resp = api.post("/modify", json=payload)
                    st.success(f"Modify response: {resp}")
                    st.session_state["order_refresh"] += 1
                except Exception as e:
                    st.error(f"Modify failed: {e}")
