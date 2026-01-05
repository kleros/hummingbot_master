## Hummingbot Log Monitor — Overview

This utility watches a Hummingbot log file for alert-worthy lines (by default, WARNING and ERROR). It remembers the last line it processed, writes structured JSON event logs, and can take automated safety actions when alerts are detected:

- Kill a running `screen` session (e.g., the Hummingbot session)
- Run a custom “cancel” command (e.g., to cancel open orders)

It is designed to be idempotent and safe to run on a schedule (e.g., via cron).


### How it works
1. Reads configuration from environment variables (paths, levels to match, commands, timeouts).
2. Loads the previous state (last processed log line) from a JSON state file.
3. Scans only the new lines in the Hummingbot log for any of the configured match levels.
4. If no alerts are found, logs an informational event and exits.
5. If alerts are found:
   - Attempts to kill the configured `screen` session.
   - If that succeeds, runs the configured cancel command.
   - Emits structured JSON events for every step and returns a non‑zero exit code if any action fails.


## Requirements

- Python 3.8+
- Access to the Hummingbot log file you want to monitor
- System dependencies available in PATH (if you enable actions):
  - `screen` (for terminating the session)
  - Your cancel/mitigation CLI (e.g., `bitfinex-maker-kit`), if configured
- File system permissions to read the log and write the state and event log files


## Files in this repo

- `Main.py`: CLI entry point and high-level orchestration
- `helper_function.py`: state, log scanning, and subprocess helpers
- `wide_logger.py`: JSON “wide event” logger


## Configuration (Environment Variables)

You can customize behavior entirely via environment variables. Defaults are shown below.

| Variable | Default | Description |
|---|---|---|
| `HB_LOG_FILE` | `/var/log/hummingbot/latest.log` | Path to the Hummingbot log file to monitor. |
| `HB_STATE_FILE` | `/tmp/hb_log_monitor.state` | JSON file where the last processed line is stored. |
| `HB_EVENT_LOG_FILE` | `/tmp/hb_log_monitor.log` | Where JSON event logs are written. |
| `HB_SCREEN_SESSION` | `hummingbot` | Name of the `screen` session to terminate on alert. |
| `HB_CANCEL_CMD` | `bitfinex-maker-kit cancel --symbol tPNKUSD` | Command to run after killing the `screen` session. |
| `HB_MATCH_LEVELS` | `ERROR,WARNING` | Comma-separated levels to match against log lines (case-insensitive). |
| `HB_CMD_TIMEOUT` | `60` | Timeout in seconds for `screen` and cancel commands. |

Notes:
- If `HB_MATCH_LEVELS` is empty or invalid, it falls back to `ERROR,WARNING`.
- If the last processed line is not found (e.g., log rotation), scanning starts from the beginning of the file.


## Usage

### Run once (manual)

```bash
# Optionally configure your environment
source .env

python3 Main.py
echo "Exit code: $?"  # 0 = ok/no failure, 2 = action failed, 1 = unexpected error
```


## Exit codes

- `0`: No alerts found or all actions succeeded
- `2`: An action failed (e.g., failed to kill `screen` or cancel command failed)
- `1`: Unexpected error while reading logs or unhandled exception
- `130`: Interrupted (Ctrl‑C)



