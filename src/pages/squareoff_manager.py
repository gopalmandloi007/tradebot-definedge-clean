"""
squareoff_manager.py

Advanced square-off utilities for the tradebot.

Usage:
    from tradebot.squareoff_manager import SquareoffManager
    sm = SquareoffManager(api_client, positions_manager, holdings_manager, symbol_manager)
    # Dry run example:
    summary = sm.squareoff_all_positions(market=True, dry_run=True)
    print(summary)

Design:
- Uses APIClient to place orders (POST /placeorder).
- If a local PositionsManager / HoldingsManager available, it will use them;
  otherwise you can pass lists of positions/holdings manually to the methods.
- Supports: Full/Partial/Selected, Market or Limit orders.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class SquareoffError(Exception):
    pass


class SquareoffManager:
    def __init__(
        self,
        api_client,
        positions_manager=None,
        holdings_manager=None,
        symbol_manager=None,
        default_variety: str = "SQUAREOFF",
    ):
        """
        Parameters:
        - api_client: instance exposing .post(path, json=...) and .get(path) (APIClient)
        - positions_manager: PositionsManager instance (optional)
        - holdings_manager: HoldingsManager instance (optional)
        - symbol_manager: symbol_manager module/class (optional, for token lookups etc.)
        - default_variety: variety string used for placeorder (SQUAREOFF)
        """
        self.api = api_client
        self.positions_manager = positions_manager
        self.holdings_manager = holdings_manager
        self.symbol_manager = symbol_manager
        self.default_variety = default_variety

    # ----------------- Helpers -----------------
    @staticmethod
    def _determine_side_from_qty(net_qty: float) -> str:
        """
        Positive net_qty => long => to exit we SELL
        Negative net_qty => short => to exit we BUY
        """
        try:
            nq = float(net_qty)
        except Exception:
            nq = 0.0
        return "SELL" if nq > 0 else "BUY"

    def _place_squareoff_order(
        self,
        exchange: str,
        tradingsymbol: str,
        quantity: int,
        order_type: Optional[str] = None,  # BUY/SELL, if None infer from quantity or callpoint
        market: bool = True,
        limit_price: Optional[float] = None,
        product_type: str = "INTRADAY",
        remarks: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Core: place a single squareoff order via /placeorder.
        Returns dict with API response or simulation summary.
        """
        if quantity <= 0:
            raise SquareoffError("quantity must be > 0 to place squareoff order")

        # infer order_type if not provided (if quantity sign or default)
        if not order_type:
            # No sign info here: default to SELL (caller should pass correct one)
            order_type = "SELL"

        payload = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "order_type": order_type,
            "quantity": str(int(quantity)),
            "product_type": product_type,
            "price_type": "MARKET" if market else "LIMIT",
            "price": "0" if market else str(limit_price if limit_price is not None else 0),
            "variety": self.default_variety,
            "remarks": remarks or f"SQUAREOFF:{tradingsymbol}",
            "validity": "DAY",
        }

        logger.debug("Squareoff payload: %s", payload)

        if dry_run:
            return {"status": "DRY", "payload": payload, "message": "Dry run - no API call made."}

        try:
            resp = self.api.post("/placeorder", json=payload)
            return {"status": "OK", "payload": payload, "response": resp}
        except Exception as e:
            logger.exception("Squareoff order failed for %s", tradingsymbol)
            return {"status": "ERROR", "payload": payload, "error": str(e)}

    # ----------------- Public operations -----------------
    def squareoff_all_positions(
        self,
        market: bool = True,
        limit_price: Optional[float] = None,
        partial_qty: Optional[int] = None,
        positions: Optional[List[Dict]] = None,
        dry_run: bool = False,
    ) -> List[Dict]:
        """
        Square off all positions retrieved from positions_manager (or provided list).
        - market: True => market orders; False => limit orders (limit_price required if False)
        - partial_qty: if provided, will attempt to close only up to this qty per position (min of net qty and partial_qty)
        - positions: optional list override (if None, will fetch from self.positions_manager)
        - dry_run: do not place real orders, just return payloads
        Returns: list of per-instrument summaries
        """
        if positions is None:
            if not self.positions_manager:
                raise SquareoffError("No positions provided and positions_manager not configured.")
            positions = self.positions_manager.get_positions()

        summaries = []
        for pos in positions:
            try:
                net_qty_raw = pos.get("net_quantity") or pos.get("netqty") or pos.get("net_qty") or pos.get("netQuantity")
                try:
                    net_qty = int(float(net_qty_raw))
                except Exception:
                    net_qty = 0
                if net_qty == 0:
                    continue

                # decide qty to squareoff
                abs_qty = abs(net_qty)
                sq_qty = abs_qty if partial_qty is None else min(abs_qty, int(partial_qty))

                # determine side to place (if net long, we SELL to close)
                order_side = self._determine_side_from_qty(net_qty)

                exchange = pos.get("exchange") or pos.get("exch") or "NSE"
                tradingsymbol = pos.get("tradingsymbol") or pos.get("symbol")
                product_type = pos.get("product_type") or pos.get("product") or "INTRADAY"

                # If limit orders requested but no limit_price provided, raise
                if not market and limit_price is None:
                    raise SquareoffError("limit_price must be provided for limit squareoff orders")

                remark = f"SQUAREOFF_POS_{tradingsymbol}"

                res = self._place_squareoff_order(
                    exchange=exchange,
                    tradingsymbol=tradingsymbol,
                    quantity=sq_qty,
                    order_type=order_side,
                    market=market,
                    limit_price=limit_price,
                    product_type=product_type,
                    remarks=remark,
                    dry_run=dry_run,
                )
                summaries.append({"symbol": tradingsymbol, "net_qty": net_qty, "sq_qty": sq_qty, "result": res})
            except Exception as e:
                logger.exception("Error while preparing squareoff for position: %s", pos)
                summaries.append({"symbol": pos.get("tradingsymbol", "<unknown>"), "error": str(e)})
        return summaries

    def squareoff_all_holdings(
        self,
        market: bool = True,
        limit_price: Optional[float] = None,
        partial_qty: Optional[int] = None,
        holdings: Optional[List[Dict]] = None,
        dry_run: bool = False,
    ) -> List[Dict]:
        """
        Square off holdings (typically equities held). We will generate SELL orders to close holdings.
        - holdings: optional override list; otherwise uses holdings_manager.get_holdings()
        - partial_qty: if provided, use min(holding_qty, partial_qty)
        """
        if holdings is None:
            if not self.holdings_manager:
                raise SquareoffError("No holdings provided and holdings_manager not configured.")
            # holdings_manager.get_holdings may return enriched holdings (with dp_qty etc.) or raw; handle both.
            holdings = self.holdings_manager.get_holdings()

        summaries = []
        for h in holdings:
            try:
                # holdings_manager might return dicts with 'dp_qty','t1_qty' or 'quantity' - try multiple keys
                qty_keys = ["dp_qty", "t1_qty", "unpledged_qty", "quantity", "trade_qty"]
                found_qty = None
                for k in qty_keys:
                    if k in h and h.get(k) not in (None, "", "0"):
                        try:
                            found_qty = int(float(h.get(k, 0)))
                            if found_qty > 0:
                                break
                        except Exception:
                            continue
                if not found_qty or found_qty == 0:
                    # try other fields or skip
                    # also check if holdings_manager returned a summary with 't1_qty' etc
                    found_qty = 0

                if found_qty == 0:
                    continue  # nothing to square off for this holding

                sq_qty = found_qty if partial_qty is None else min(found_qty, int(partial_qty))
                exchange = None
                tradingsymbol = None
                # holdings entries earlier were shaped with list under 'tradingsymbol' - handle both
                if "tradingsymbol" in h and isinstance(h["tradingsymbol"], list):
                    # pick first mapping (NSE preferred)
                    first = h["tradingsymbol"][0]
                    exchange = first.get("exchange") or first.get("exch")
                    tradingsymbol = first.get("tradingsymbol")
                else:
                    exchange = h.get("exchange") or h.get("exch") or "NSE"
                    tradingsymbol = h.get("tradingsymbol") or h.get("symbol")

                if tradingsymbol is None:
                    logger.warning("Skipping holding without tradingsymbol: %s", h)
                    continue

                # infer product_type (usually CNC for holdings)
                product_type = h.get("product_type") or "CNC"

                if not market and limit_price is None:
                    raise SquareoffError("limit_price must be provided for limit squareoff orders")

                remark = f"SQUAREOFF_HOLD_{tradingsymbol}"

                res = self._place_squareoff_order(
                    exchange=exchange,
                    tradingsymbol=tradingsymbol,
                    quantity=sq_qty,
                    order_type="SELL",
                    market=market,
                    limit_price=limit_price,
                    product_type=product_type,
                    remarks=remark,
                    dry_run=dry_run,
                )
                summaries.append({"symbol": tradingsymbol, "holding_qty": found_qty, "sq_qty": sq_qty, "result": res})
            except Exception as e:
                logger.exception("Error while preparing squareoff for holding: %s", h)
                summaries.append({"symbol": h.get("tradingsymbol", "<unknown>"), "error": str(e)})
        return summaries

    def squareoff_selected(
        self,
        tradingsymbol: str,
        side: Optional[str] = None,
        qty: Optional[int] = None,
        market: bool = True,
        limit_price: Optional[float] = None,
        exchange: Optional[str] = "NSE",
        product_type: str = "INTRADAY",
        dry_run: bool = False,
        remarks: Optional[str] = None,
    ) -> Dict:
        """
        Squareoff a single selected symbol.
        - tradingsymbol: trading symbol string (as used by your broker)
        - side: BUY/SELL (if None, caller must ensure which side to use)
        - qty: required (if None, will try to infer via holdings/positions)
        - market: Market or Limit
        - limit_price: required if market=False
        """
        # try to infer qty from positions_manager / holdings_manager if not provided
        inferred_qty = qty
        if inferred_qty is None:
            # check positions
            try:
                if self.positions_manager:
                    pos_list = self.positions_manager.get_positions()
                    for p in pos_list:
                        if p.get("tradingsymbol") == tradingsymbol:
                            net_qty = int(float(p.get("net_quantity", 0)))
                            if net_qty != 0:
                                inferred_qty = abs(net_qty)
                                if side is None:
                                    side = self._determine_side_from_qty(net_qty)
                                break
            except Exception:
                pass

        if inferred_qty is None and self.holdings_manager:
            try:
                holdings = self.holdings_manager.get_holdings()
                for h in holdings:
                    # holdings may contain nested tradingsymbol list - search those
                    tlist = h.get("tradingsymbol")
                    if isinstance(tlist, list):
                        for mapping in tlist:
                            if mapping.get("tradingsymbol") == tradingsymbol:
                                # get qty
                                inferred_qty = int(float(h.get("t1_qty") or h.get("dp_qty") or h.get("quantity") or 0))
                                break
                    elif h.get("tradingsymbol") == tradingsymbol:
                        inferred_qty = int(float(h.get("t1_qty") or h.get("dp_qty") or h.get("quantity") or 0))
                    if inferred_qty:
                        break
            except Exception:
                pass

        if inferred_qty is None or inferred_qty == 0:
            raise SquareoffError(f"Could not infer quantity for {tradingsymbol}. Provide qty explicitly.")

        if side is None:
            # default to SELL to close long (caller should choose)
            side = "SELL"

        if not market and limit_price is None:
            raise SquareoffError("limit_price must be provided for limit squareoff orders")

        # place order
        remark = remarks or f"SQUAREOFF_SEL_{tradingsymbol}"
        res = self._place_squareoff_order(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            quantity=inferred_qty,
            order_type=side,
            market=market,
            limit_price=limit_price,
            product_type=product_type,
            remarks=remark,
            dry_run=dry_run,
        )

        return {"symbol": tradingsymbol, "qty": inferred_qty, "side": side, "result": res}
