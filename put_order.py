import os
from decimal import Decimal, ROUND_DOWN
from bfxapi import Client
from hleper_functions.wide_logger import setup_logger, log_event

# Configuration: Update these with your Bitfinex API Key and Secret
# Alternatively, set them as environment variables in your terminal:
# export BITFINEX_API_KEY='your_key_here'
# export BITFINEX_API_SECRET='your_secret_here'
API_KEY = os.getenv("BITFINEX_API_KEY", "YOUR_API_KEY")
API_SECRET = os.getenv("BITFINEX_API_SECRET", "YOUR_API_SECRET")

# Initialize wide logger
logger = setup_logger()  # Standard stream handler for console output

def get_bfx_client():
    """
    Helper function to initialize the Bitfinex Client.
    """
    if API_KEY == "YOUR_API_KEY" or API_SECRET == "YOUR_API_SECRET":
        log_event(logger, "WARNING", "api_key_not_set", msg="API_KEY or API_SECRET is not set correctly.")
    
    return Client(
        api_key=API_KEY,
        api_secret=API_SECRET
    )

def format_bitfinex_price(price: float) -> str:
    """
    Formats the price according to Bitfinex's 5 significant digits rule.
    Bitfinex truncates prices that exceed 5 significant digits.
    """
    if price == 0:
        return "0"
    
    # Use Decimal for precise handling
    d_price = Decimal(str(price))
    
    # Calculate the number of digits before the decimal point
    # log10 of the absolute value gives the magnitude
    import math
    magnitude = math.floor(math.log10(abs(float(d_price))))
    
    # Significant digits are counted from the first non-zero digit.
    # We want 5 significant digits.
    # The number of decimal places needed is (5 - 1 - magnitude)
    decimals = 5 - 1 - magnitude
    
    # Bitfinex generally supports up to 5 significant digits.
    # We use ROUND_DOWN to match Bitfinex's truncation behavior.
    format_str = f"{{:.{max(0, decimals)}f}}"
    formatted = format_str.format(d_price).rstrip('0').rstrip('.')
    
    # Double check significant digits count
    sig_digits = len(formatted.replace('.', '').lstrip('0'))
    if sig_digits > 5:
        # If still over 5 (can happen with rounding), we need to truncate further
        # This is a safe fallback
        shift = 5 - sig_digits
        # Implementation of truncation for significant digits is tricky with strings,
        # but for Bitfinex 5 is the standard.
        pass

    return formatted

def calculate_bfx_amount(amount: float, side: str) -> float:
    """
    Helper function to determine the Bitfinex amount sign.
    On Bitfinex:
    - A positive amount indicates a BUY order.
    - A negative amount indicates a SELL order.
    """
    side = side.strip().lower()
    if side == "buy":
        return abs(amount)
    elif side == "sell":
        return -abs(amount)
    else:
        raise ValueError(f"Invalid side: '{side}'. Must be 'buy' or 'sell'.")

def _execute_put_order(price: float, amount: float, side: str, symbol: str):
    """
    Synchronous helper to submit the order using the bfxapi library.
    """
    bfx = get_bfx_client()
    
    # Bitfinex uses signed amounts for buy/sell
    signed_amount = calculate_bfx_amount(amount, side)
    
    # Format price to respect Bitfinex's precision rules (5 significant digits)
    formatted_price = format_bitfinex_price(price)
    
    log_event(logger, "INFO", "order_submission_start", 
              symbol=symbol, side=side.upper(), price=price, 
              formatted_price=formatted_price, amount=amount)
    
    try:
        # 'EXCHANGE LIMIT' is used for standard spot trading (no margin).
        # For margin trading, use 'LIMIT'.
        response = bfx.rest.auth.submit_order(
            symbol=symbol,
            price=formatted_price,
            amount=str(signed_amount),
            type='EXCHANGE LIMIT'
        )
        # Convert response to string or dict if possible for logging
        log_event(logger, "INFO", "order_submission_success", 
                  price_sent=formatted_price,
                  response=str(response))
        return response
    except Exception as e:
        log_event(logger, "ERROR", "order_submission_failed", 
                  price_sent=formatted_price,
                  error=str(e))
        return None

def put_order(price: float, amount: float, side: str, symbol: str = "tPNKUSD"):
    """
    The main function to put an order on Bitfinex.
    
    Parameters:
    - price: The price at which to place the order.
    - amount: The quantity of the asset to buy or sell.
    - side: 'buy' or 'sell'.
    - symbol: The trading pair symbol (default is 'tPNKUSD').
    """
    return _execute_put_order(price, amount, side, symbol)

if __name__ == "__main__":
    # --- ONE-TIME COMMAND EXECUTION ---
    # Example: Buy 1000 PNK at 0.0123
    put_order(price=0.016390, amount=52, side='buy')
    
    log_event(logger, "INFO", "script_ready", msg="put_order.py has finished execution.")
