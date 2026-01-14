# Hummingbot Management Tools

This repository provides a set of scripts to manage and monitor Hummingbot states on Bitfinex.

## Overview

The following scripts are available in this repo for managing the state of Hummingbot:
- **`spread.py`**: An automated monitor that calculates the bid-ask spread and triggers safety actions (killing the bot and cancelling orders) if the spread threshold is breached.
- **`put_order.py`**: A manual script for placing single orders on Bitfinex, used to fill an order in the bot or change the best bid/ask.

---

## Hummingbot Spread Monitor — Detailed Overview

This utility monitors the order book of a Hummingbot instance by running a "list" command. It calculates the current bid-ask spread and, if it exceeds a configured threshold (or if the book is crossed), takes automated safety actions:

- Kill a running `screen` session (e.g., the Hummingbot session)
- Run a custom “cancel” command (e.g., to cancel all open orders)

It is designed to be idempotent and safe to run on a schedule (e.g., via cron).


### How it works
1. Reads configuration from environment variables (commands, thresholds, timeouts).
2. Runs the configured "list" command to fetch open orders.
3. Parses the orders and identifies the best bid and best ask (filtering by a minimum order size if configured).
4. Calculates the percentage spread relative to the mid-price.
5. Persists the current book state (best bid, best ask, spread) to a JSON state file.
6. If the spread is within limits, logs an informational event and exits.
7. If the spread exceeds the threshold or is **negative** (indicating a crossed book):
   - Attempts to kill the configured `screen` session (terminating the bot).
   - If that succeeds, runs the configured cancel command to clear the book.
   - Emits structured JSON events for every step and returns a non-zero exit code if any action fails.


## Requirements

- Python 3.8+
- System dependencies available in PATH (if you enable actions):
  - `screen` (for terminating the session)
  - Your list and cancel CLI (e.g., `bitfinex-maker-kit`), if configured
- File system permissions to write the state and event log files


## Files in this repo

- `spread.py`: CLI entry point and high-level orchestration
- `put_order.py`: Manual script to place a single order on Bitfinex
- `hleper_functions/`: directory containing helper modules
  - `helper_function.py`: state and subprocess helpers
  - `helper_functions_spread.py`: spread calculation and order parsing helpers
  - `wide_logger.py`: JSON “wide event” logger


## Configuration (Environment Variables)

You can customize behavior entirely via environment variables. Defaults are shown below.

| Variable | Default | Description |
|---|---|---|
| `SPREAD_STATE_FILE` | `~/hummingbot_master/states/spread.state` | JSON file where the current book state is stored. |
| `SPREAD_EVENT_LOG_FILE` | `~/hummingbot_master/logs/spread_log_monitor.log` | Where JSON event logs are written. |
| `HB_SCREEN_SESSION` | `hummingbot` | Name of the `screen` session to terminate if spread threshold breached. |
| `HB_CANCEL_CMD` | `bitfinex-maker-kit cancel --symbol tPNKUSD` | Command to run after killing the `screen` session. |
| `HB_LIST_CMD` | `bitfinex-maker-kit list --symbol tPNKUSD` | Command to list open orders for spread checking. |
| `HB_SPREAD_PERCENT_THRESHOLD` | `0.5` | Spread threshold (in percent) to trigger safety actions. |
| `HB_MIN_ORDER_AMOUNT` | `0` | Minimum order amount to consider when calculating spread. |
| `HB_CMD_TIMEOUT` | `60` | Timeout in seconds for commands. |

Notes:
- **Safety Trigger**: The bot termination and order cancellation are triggered if the spread is either **negative** (crossed book) or exceeds the `HB_SPREAD_PERCENT_THRESHOLD`.


## Usage

### Run once (manual)

```bash
# Optionally configure your environment
source .env

python3 spread.py
echo "Exit code: $?"  # 0 = ok/no breach, 2 = action failed, 1 = unexpected error
```


## Manual Order Placement (`put_order.py`)

In addition to the spread monitor, there is a standalone script `put_order.py` for placing manual orders on Bitfinex. This is useful for:
- Manually filling an order for the bot.
- Manually adjusting the best bid or best ask in the order book.

**Note**: The configuration for this script (price, amount, side, and symbol) is currently **hardcoded** at the bottom of the file in the `if __name__ == "__main__":` block. You must edit the script directly to change these values before running it:

```bash
python3 put_order.py
```


## Exit codes

- `0`: Spread is healthy or safety actions succeeded
- `2`: An action failed (e.g., failed to kill `screen` or cancel command failed)
- `1`: Unexpected error or unhandled exception
- `130`: Interrupted (Ctrl-C)
