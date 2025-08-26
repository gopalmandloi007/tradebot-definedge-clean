import streamlit as st
import time
from core.api_client import APIClient
from core.symbol_manager import SymbolManager
from core.order_manager import OrderManager
from core.historical_data import HistoricalData

# Initialize API
api_client = APIClient()
symbol_manager = SymbolManager()
order_manager = OrderManager(api_client)
historical = HistoricalData(api_client)

st.set_page_config(page_title="Trading App", layout="wide")

st.title("📈 Advanced Order Placement")

# --- SYMBOL SELECTION ---
symbols = symbol_manager.get_all_symbols()  # Load from master
symbol_list = [s["tradingsymbol"] for s in symbols]

col1, col2 = st.columns([2,1])
with col1:
    selected_symbol = st.selectbox("Select Symbol", symbol_list, key="symbol_select")
with col2:
    exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO", "MCX"], key="exchange")

# Fetch LTP live (simulate via historical_data or API call)
ltp = historical.get_ltp(selected_symbol, exchange)
st.metric(label="Live Price (LTP)", value=f"{ltp:.2f}")

# --- ORDER INPUTS ---
col1, col2, col3 = st.columns(3)
with col1:
    side = st.radio("Side", ["BUY", "SELL"], key="order_side")
with col2:
    order_type = st.selectbox("Order Type", ["LIMIT", "MARKET", "SL-LIMIT", "SL-MARKET"], key="order_type")
with col3:
    product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], key="product_type")

# --- QTY or AMOUNT ---
col1, col2 = st.columns(2)
with col1:
    input_mode = st.radio("Order Mode", ["Quantity", "Amount"], key="input_mode")
with col2:
    if input_mode == "Quantity":
        qty = st.number_input("Quantity", min_value=1, step=1, value=1, key="qty")
    else:
        amount = st.number_input("Amount ₹", min_value=100, step=100, value=1000, key="amount")
        qty = int(amount // ltp) if ltp > 0 else 0
        st.write(f"Calculated Qty: {qty}")

# --- PRICE FIELDS ---
if order_type == "MARKET":
    price = 0
    trigger_price = None
else:
    price = st.number_input("Price", min_value=0.0, value=float(ltp), step=0.05, key="price")
    trigger_price = None
    if order_type in ["SL-LIMIT", "SL-MARKET"]:
        trigger_price = st.number_input("Trigger Price", min_value=0.0, value=float(ltp), step=0.05, key="trigger_price")

remarks = st.text_input("Remarks (optional)", key="remarks")

# --- PLACE ORDER BUTTON ---
if st.button("🚀 Place Order"):
    order_payload = {
        "exchange": exchange,
        "order_type": side,
        "price_type": order_type,
        "product_type": product_type,
        "quantity": str(qty),
        "tradingsymbol": selected_symbol,
        "price": str(price),
        "remarks": remarks,
        "validity": "DAY"
    }

    if trigger_price:
        order_payload["trigger_price"] = str(trigger_price)

    st.json(order_payload)  # Debug payload

    response = order_manager.place_order(order_payload)

    if response.get("status") == "SUCCESS":
        st.success(f"✅ Order Placed! Order ID: {response.get('order_id')}")
    else:
        st.error(f"❌ Order Failed: {response.get('message')}")
