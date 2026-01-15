import json
import os
import logging
from typing import List, Tuple, Optional, Dict, Any
from bfxapi import Client
from hleper_functions.wide_logger import log_event

def calculate_mid_price(best_bid: Optional[float], best_ask: Optional[float]) -> float:
    """
    Calculate mid price from best bid and best ask.
    """
    if best_bid is None or best_ask is None or best_bid <= 0 or best_ask <= 0:
        return 0.0
    return (best_bid + best_ask) / 2.0

def calculate_liquidity(orders: List[dict], mid_price: float, percentage: float = 2.0) -> Tuple[float, float]:
    """
    Calculate total liquidity (amount) within ±percentage% of the mid_price.
    Returns (bid_liquidity, ask_liquidity).
    """
    if mid_price <= 0:
        return 0.0, 0.0
        
    lower_bound = mid_price * (1 - percentage / 100.0)
    upper_bound = mid_price * (1 + percentage / 100.0)
    
    bid_liquidity = sum(o["amount"] * o["price"] for o in orders if o["side"] == "BUY" and o["price"] >= lower_bound)
    ask_liquidity = sum(o["amount"] * o["price"] for o in orders if o["side"] == "SELL" and o["price"] <= upper_bound)
    
    return bid_liquidity, ask_liquidity

def read_assets_state(file_path: str) -> Dict[str, Any]:
    """
    Read the previous asset state from a JSON file.
    """
    full_path = os.path.expanduser(file_path)
    if not os.path.exists(full_path):
        return {}
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def fetch_inventory(api_key: str, api_secret: str, logger: Optional[logging.Logger] = None) -> Dict[str, float]:
    """
    Fetch current PNK and USD balances from Bitfinex exchange wallets.
    """
    if not api_key or not api_secret:
        if logger:
            log_event(logger, "WARNING", "fetch_inventory_missing_keys", msg="API_KEY or API_SECRET is not set.")
        return {"PNK": 0.0, "USD": 0.0}
    
    bfx = Client(api_key=api_key, api_secret=api_secret)
    try:
        # The correct method name in bitfinex-api-py is get_wallets()
        wallets = bfx.rest.auth.get_wallets()
        inventory = {"PNK": 0.0, "USD": 0.0}
        for wallet in wallets:
            # Based on Bitfinex API response, the field is wallet_type
            if wallet.wallet_type == "exchange":
                if wallet.currency == "PNK":
                    inventory["PNK"] = float(wallet.balance)
                elif wallet.currency == "USD":
                    inventory["USD"] = float(wallet.balance)
        print(inventory)
        return inventory
    except Exception as e:
        if logger:
            log_event(logger, "ERROR", "fetch_inventory_failed", error=str(e))
        # Returning zeros as fallback.
        return {"PNK": 0.0, "USD": 0.0}

def calculate_asset_metrics(pnk_amount: float, usd_amount: float, mid_price: float) -> Dict[str, Any]:
    """
    Calculate total value and proportions of assets.
    """
    pnk_value_usd = pnk_amount * mid_price
    total_value = pnk_value_usd + usd_amount
    
    if total_value > 0:
        pnk_proportion = (pnk_value_usd / total_value) * 100.0
        usd_proportion = (usd_amount / total_value) * 100.0
    else:
        pnk_proportion = 0.0
        usd_proportion = 0.0
        
    return {
        "pnk_amount": pnk_amount,
        "usd_amount": usd_amount,
        "total_value": total_value,
        "pnk_proportion": pnk_proportion,
        "usd_proportion": usd_proportion
    }
