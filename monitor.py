import os
import sys
from typing import Any, Dict
from hleper_functions.wide_logger import setup_logger, log_event
from hleper_functions.helper_function import atomic_write_state
from hleper_functions.helper_functions_spread import (
    run_list_command,
    parse_orders_from_text,
    split_filter_sort_orders,
    compute_spread_percent_mid,
)
from hleper_functions.helper_functions_monitor import (
    calculate_mid_price,
    calculate_liquidity,
    read_assets_state,
    fetch_inventory,
    calculate_asset_metrics,
    fetch_ticker_price,
)

def get_env_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    """
    status_log_file = os.environ.get("STATUS_LOG_FILE", "~/hummingbot_master/logs/status.log")
    assets_state_file = os.environ.get("ASSETS_STATE_FILE", "~/hummingbot_master/states/assets.state")
    list_cmd = os.environ.get("HB_LIST_CMD", "bitfinex-maker-kit list --symbol tPNKUSD")
    min_amount = float(os.environ.get("HB_MIN_ORDER_AMOUNT", "0"))
    timeout_s = int(os.environ.get("HB_CMD_TIMEOUT", "60"))
    api_key = os.environ.get("BITFINEX_API_KEY", "")
    api_secret = os.environ.get("BITFINEX_API_SECRET", "")
    
    return {
        "status_log_file": status_log_file,
        "assets_state_file": assets_state_file,
        "list_cmd": list_cmd,
        "min_amount": min_amount,
        "timeout_s": timeout_s,
        "api_key": api_key,
        "api_secret": api_secret,
    }

def main() -> int:
    cfg = get_env_config()
    status_log_file = cfg["status_log_file"]
    assets_state_file = cfg["assets_state_file"]
    list_cmd = cfg["list_cmd"]
    min_amount = cfg["min_amount"]
    timeout_s = cfg["timeout_s"]
    api_key = cfg["api_key"]
    api_secret = cfg["api_secret"]
    
    try:
        # Initialize wide_logger with the status log file from env
        logger = setup_logger(status_log_file)
        
        # 1. Fetch current open orders using the configured list command
        rc, stdout, stderr = run_list_command(list_cmd, timeout_s)
        if rc != 0:
            log_event(
                logger, 
                "ERROR", 
                "fetch_orders_failed", 
                rc=rc, 
                stderr=stderr, 
                cmd=list_cmd
            )
            return 1
            
        # 2. Parse orders and filter by minimum amount
        orders = parse_orders_from_text(stdout)
        buy_prices, sell_prices = split_filter_sort_orders(orders, min_amount)
        
        # 3. Get best bid and ask to calculate spread and mid price
        best_bid = buy_prices[0] if buy_prices else None
        best_ask = sell_prices[0] if sell_prices else None
        
        # 4. Calculate spread percentage
        spread_percent = compute_spread_percent_mid(best_bid, best_ask)
        
        # 5. Calculate mid price (average of best bid and best ask)
        mid_price = calculate_mid_price(best_bid, best_ask)
        
        # 6. Calculate total liquidity in USD within ±2% of mid price
        bid_liq_usd_2pct, ask_liq_usd_2pct = calculate_liquidity(orders, mid_price, 2.0)

        # 7. Asset and Inventory Tracking
        # Read previous state
        prev_state = read_assets_state(assets_state_file)
        
        # Fetch current inventory from Bitfinex
        inventory = fetch_inventory(api_key, api_secret, logger=logger)
        pnk_amount = inventory["PNK"]
        usd_amount = inventory["USD"]
        
        # Fetch current PNK price from Bitfinex API
        pnk_price = fetch_ticker_price("tPNKUSD", logger=logger)
        # Use mid_price as fallback if ticker fetch fails
        if pnk_price <= 0:
            pnk_price = mid_price
            
        # Calculate current metrics using PNK price from API instead of local mid_price
        metrics = calculate_asset_metrics(pnk_amount, usd_amount, pnk_price)
        
        # Update assets state file
        new_state = {
            "mid_price": mid_price,
            "pnk_price": pnk_price,
            "pnk_amount": pnk_amount,
            "usd_amount": usd_amount,
            "total_value": metrics["total_value"]
        }
        atomic_write_state(assets_state_file, new_state)
        
        # 8. Log the status report with all metrics for dashboards/alerts
        log_event(
            logger,
            "INFO",
            "strategy_status",
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            pnk_price=pnk_price,
            spread_percent=spread_percent,
            bid_liquidity_usd_2pct=bid_liq_usd_2pct,
            ask_liquidity_usd_2pct=ask_liq_usd_2pct,
            buys_count=len(buy_prices),
            sells_count=len(sell_prices),
            # Asset metrics
            pnk_amount=pnk_amount,
            usd_amount=usd_amount,
            total_value=metrics["total_value"],
            pnk_proportion=f"{metrics['pnk_proportion']:.2f}%",
            usd_proportion=f"{metrics['usd_proportion']:.2f}%",
            # Previous state for comparison (optional but helpful for dashboards)
            prev_total_value=prev_state.get("total_value")
        )
        
        return 0
    except Exception as e:
        # Fallback print if logger setup or execution fails critically
        print(f"Critical error in monitor script: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
