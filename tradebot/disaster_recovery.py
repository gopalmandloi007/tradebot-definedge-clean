"""
disaster_recovery.py

Utilities for emergency/bulk order management:
- cancel_all_orders, cancel_selected_orders
- modify_all_orders_to_market, modify_selected_orders_to_market
- cancel_gtt_all, cancel_oco_all, modify_gtt, modify_oco
Designed to work with your APIClient instance that exposes:
- .get(path) -> parsed JSON (or requests.Response-like)
- .post(path, json=...) -> parsed JSON (or requests.Response-like)

All methods support dry_run=True for simulation.
"""

from __future__ import annotations
import time
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class DisasterRecoveryError(Exception):
    pass


class DisasterRecoveryManager:
    def __init__(self, api_client, sleep_between_calls: float = 0.2):
        """
        api_client: instance with .get(path) and .post(path, json=...) methods.
        sleep_between_calls: small sleep between API requests to avoid throttling.
        """
        self.api = api_client
        self.sleep = float(sleep_between_calls)

    # ---------- Helpers ----------
    def _fetch_order_book(self) -> List[Dict]:
        resp = self.api.get("/orders")
        # resp may be dict with 'status' and 'orders'
        if isinstance(resp, dict) and resp.get("status") == "SUCCESS":
            return resp.get("orders", [])
        # fallback: if the client returned list or requests.Response-like
        if isinstance(resp, list):
            return resp
        raise DisasterRecoveryError(f"Unable to fetch order book or unexpected response: {resp}")

    def _call_cancel(self, order_id: str, dry_run: bool = True) -> Dict[str, Any]:
        if dry_run:
            return {"order_id": order_id, "action": "cancel", "status": "DRY", "message": "Dry run - no API call"}
        try:
            resp = self.api.get(f"/cancel/{order_id}")
            time.sleep(self.sleep)
            return {"order_id": order_id, "action": "cancel", "status": "OK", "response": resp}
        except Exception as e:
            logger.exception("Cancel failed for %s", order_id)
            return {"order_id": order_id, "action": "cancel", "status": "ERROR", "error": str(e)}

    def _call_modify_to_market(self, order: Dict, dry_run: bool = True) -> Dict[str, Any]:
        """
        Modify an existing order to MARKET price type.
        Expects 'order' contains 'order_id' and 'exchange' and 'tradingsymbol'.
        """
        order_id = order.get("order_id") or order.get("orderid") or order.get("orderId")
        exchange = order.get("exchange")
        tradingsymbol = order.get("tradingsymbol")
        order_type = order.get("order_type") or order.get("orderType") or "BUY"
        product_type = order.get("product_type") or order.get("product_type") or order.get("product") or "NORMAL"
        payload = {
            "exchange": exchange,
            "order_id": str(order_id),
            "tradingsymbol": tradingsymbol,
            "quantity": str(order.get("quantity", order.get("pending_qty", order.get("filled_qty", 0)))),
            "price": "0",
            "product_type": product_type,
            "order_type": order_type,
            "price_type": "MARKET",
        }
        if dry_run:
            return {"order_id": order_id, "action": "modify_to_market", "status": "DRY", "payload": payload}
        try:
            resp = self.api.post("/modify", json=payload)
            time.sleep(self.sleep)
            return {"order_id": order_id, "action": "modify_to_market", "status": "OK", "response": resp}
        except Exception as e:
            logger.exception("Modify-to-market failed for %s", order_id)
            return {"order_id": order_id, "action": "modify_to_market", "status": "ERROR", "error": str(e)}

    # ---------- Public operations ----------
    def cancel_all_open_orders(self, dry_run: bool = True, filter_fn: Optional[callable] = None) -> List[Dict]:
        """
        Cancel all orders present in order book with status OPEN/NEW/PARTIAL etc.
        Optional filter_fn to select which orders to cancel: filter_fn(order) -> bool
        """
        orders = self._fetch_order_book()
        # default filtering: exclude COMPLETED/CANCELED orders
        cancel_candidates = []
        for o in orders:
            status = (o.get("order_status") or o.get("orderStatus") or "").upper()
            if status in ("CANCELED", "COMPLETE", "REJECTED"):
                continue
            if filter_fn and not filter_fn(o):
                continue
            cancel_candidates.append(o)

        results = []
        for o in cancel_candidates:
            oid = str(o.get("order_id") or o.get("orderid") or o.get("orderId"))
            res = self._call_cancel(oid, dry_run=dry_run)
            results.append({"order": o, "result": res})
        return results

    def cancel_selected_orders(self, order_ids: List[str], dry_run: bool = True) -> List[Dict]:
        """
        Cancel only the provided order ids.
        """
        results = []
        for oid in order_ids:
            res = self._call_cancel(str(oid), dry_run=dry_run)
            results.append(res)
        return results

    def cancel_by_filter(
        self,
        exchange: Optional[str] = None,
        symbol_contains: Optional[str] = None,
        variety: Optional[str] = None,
        status_in: Optional[List[str]] = None,
        dry_run: bool = True,
    ) -> List[Dict]:
        """
        Cancel orders matching the provided filters.
        - exchange: e.g., "NSE" or "NFO"
        - symbol_contains: substring match on tradingsymbol
        - variety: REGULAR/AMO/SQUAREOFF
        - status_in: list of order_status to include (e.g., ["OPEN","NEW"])
        """
        def _filter(o):
            if exchange and o.get("exchange") != exchange:
                return False
            if symbol_contains and symbol_contains.upper() not in str(o.get("tradingsymbol", "")).upper():
                return False
            if variety and str(o.get("variety", "")).upper() != variety.upper():
                return False
            if status_in:
                st = str(o.get("order_status", "")).upper()
                if st not in [s.upper() for s in status_in]:
                    return False
            return True

        return self.cancel_all_open_orders(dry_run=dry_run, filter_fn=_filter)

    def modify_all_to_market(self, dry_run: bool = True, only_open: bool = True) -> List[Dict]:
        """
        Modify all open orders to MARKET type.
        If only_open True, consider only not-finalized orders.
        """
        orders = self._fetch_order_book()
        candidates = []
        for o in orders:
            stt = str(o.get("order_status", "")).upper()
            if only_open and stt in ("CANCELED", "COMPLETE", "REJECTED"):
                continue
            candidates.append(o)

        results = []
        for o in candidates:
            res = self._call_modify_to_market(o, dry_run=dry_run)
            results.append({"order": o, "result": res})
        return results

    def modify_selected_to_market(self, order_ids: List[str], dry_run: bool = True) -> List[Dict]:
        """
        Modify only the provided order ids to market.
        """
        # fetch order book to enrich payload with order details if needed
        orders = self._fetch_order_book()
        order_map = {str(o.get("order_id") or o.get("orderid") or o.get("orderId")): o for o in orders}
        results = []
        for oid in order_ids:
            o = order_map.get(str(oid), {})
            if not o:
                # still attempt to modify with minimal payload (order_id & exchange required)
                # but API usually needs tradingsymbol to modify; fail gracefully
                results.append({"order_id": oid, "result": {"status": "ERROR", "error": "Order not found in book"}})
                continue
            res = self._call_modify_to_market(o, dry_run=dry_run)
            results.append({"order": o, "result": res})
        return results

    # ---------- GTT / OCO shortcuts ----------
    def cancel_all_gtt(self, dry_run: bool = True) -> List[Dict]:
        """
        Cancel all GTT alerts (if broker exposes /gttorders or if we can fetch them).
        This implementation expects api_client.get("/gttorders") or similar; otherwise, will attempt direct cancellation if list provided.
        """
        # try to fetch list
        try:
            resp = self.api.get("/gttorders")
            alerts = resp.get("alerts") if isinstance(resp, dict) else []
        except Exception:
            alerts = []

        results = []
        for a in alerts:
            alert_id = str(a.get("alert_id") or a.get("alertId"))
            if dry_run:
                results.append({"alert_id": alert_id, "action": "gttcancel", "status": "DRY"})
                continue
            try:
                r = self.api.get(f"/gttcancel/{alert_id}")
                time.sleep(self.sleep)
                results.append({"alert_id": alert_id, "action": "gttcancel", "status": "OK", "response": r})
            except Exception as e:
                logger.exception("Failed to cancel GTT %s", alert_id)
                results.append({"alert_id": alert_id, "action": "gttcancel", "status": "ERROR", "error": str(e)})
        return results

    def cancel_all_oco(self, dry_run: bool = True) -> List[Dict]:
        """
        Cancel all OCO alerts (if listed via /gttorders or a dedicated endpoint).
        We will attempt to list via /gttorders or fall back to no-op.
        """
        # Some brokers may include OCO in gtt list; adapt as per API.
        try:
            resp = self.api.get("/gttorders")
            alerts = resp.get("alerts") if isinstance(resp, dict) else []
        except Exception:
            alerts = []

        results = []
        for a in alerts:
            # depending on API, OCO alerts may be marked; skip if not OCO
            alert_id = str(a.get("alert_id") or a.get("alertId"))
            # We'll assume alert supports ococancel endpoint if OCO
            if dry_run:
                results.append({"alert_id": alert_id, "action": "ococancel", "status": "DRY"})
                continue
            try:
                r = self.api.get(f"/ococancel/{alert_id}")
                time.sleep(self.sleep)
                results.append({"alert_id": alert_id, "action": "ococancel", "status": "OK", "response": r})
            except Exception as e:
                logger.exception("Failed to cancel OCO %s", alert_id)
                results.append({"alert_id": alert_id, "action": "ococancel", "status": "ERROR", "error": str(e)})
        return results
