import os
import sys
from typing import Any, Dict
from hleper_functions.wide_logger import setup_logger, log_event
from hleper_functions.helper_function import (
    atomic_write_state,
    kill_screen_session,
    run_cancel_command,
)
from hleper_functions.helper_functions_spread import (
    run_list_command,
    parse_orders_from_text,
    split_filter_sort_orders,
    compute_spread_percent_mid,
)


def get_env_config() -> Dict[str, Any]:
    state_file = os.environ.get("SPREAD_STATE_FILE", "~/hummingbot_master/states/spread.state")
    event_log_file = os.environ.get("SPREAD_EVENT_LOG_FILE", "~/hummingbot_master/logs/spread_log_monitor.log")
    screen_session = os.environ.get("HB_SCREEN_SESSION", "hummingbot")
    cancel_cmd = os.environ.get("HB_CANCEL_CMD", "bitfinex-maker-kit cancel --symbol tPNKUSD")
    list_cmd = os.environ.get("HB_LIST_CMD", "bitfinex-maker-kit list --symbol tPNKUSD")
    min_order_amount = float(os.environ.get("HB_MIN_ORDER_AMOUNT", "0"))
    spread_percent_threshold = float(os.environ.get("HB_SPREAD_PERCENT_THRESHOLD", "0.5"))
    timeout_s = int(os.environ.get("HB_CMD_TIMEOUT", "60"))

    return {
        "state_file": state_file,
        "event_log_file": event_log_file,
        "screen_session": screen_session,
        "cancel_cmd": cancel_cmd,
        "list_cmd": list_cmd,
        "min_order_amount": min_order_amount,
        "spread_percent_threshold": spread_percent_threshold,
        "timeout_s": timeout_s,
    }


def main() -> int:
    cfg = get_env_config()
    state_file = cfg["state_file"]
    event_log_file = cfg["event_log_file"]
    timeout_s = cfg["timeout_s"]
    session_name = cfg["screen_session"]
    cancel_cmd = cfg["cancel_cmd"]
    list_cmd = cfg["list_cmd"]
    min_order_amount = cfg["min_order_amount"]
    spread_percent_threshold = cfg["spread_percent_threshold"]
    try:
        logger = setup_logger(event_log_file)
        log_event(
            logger,
            "INFO",
            "run_start",
            mode="spread_check",
            state_file=state_file,
            list_cmd=list_cmd,
            min_order_amount=min_order_amount,
            spread_threshold_percent=spread_percent_threshold,
            timeout_s=timeout_s,
        )
        # Run list command, parse orders, compute spread; treat threshold breach as "match"
        rc_list, out_list, err_list = run_list_command(list_cmd, timeout_s)
        if rc_list != 0:
            log_event(
                logger,
                "ERROR",
                "list_orders_failed",
                rc=rc_list,
                cmd=list_cmd,
                stderr=err_list,
            )
            return 1
        orders = parse_orders_from_text(out_list)
        buy_prices_desc, sell_prices_asc = split_filter_sort_orders(orders, min_order_amount)
        best_bid = buy_prices_desc[0] if buy_prices_desc else None
        best_ask = sell_prices_asc[0] if sell_prices_asc else None
        spread_percent = compute_spread_percent_mid(best_bid, best_ask)
        matched = (
            spread_percent is not None
            and (spread_percent < 0.0 or spread_percent >= spread_percent_threshold)
        )
        state = (
            f"best_bid={best_bid} best_ask={best_ask} spread%={spread_percent:.6f} "
            f"threshold%={spread_percent_threshold} buys={len(buy_prices_desc)} sells={len(sell_prices_asc)}"
            if spread_percent is not None
            else "insufficient_book_depth"
        )
        # Persist a minimal state note for traceability
        try:
            atomic_write_state(state_file, {"state": state})
        except Exception as e:
            log_event(logger, "WARNING", "state_write_failed", error=str(e), state_file=state_file)
            # Continue anyway

        if not matched:
            log_event(
                logger,
                "INFO",
                "spread_ok",
                best_bid=best_bid,
                best_ask=best_ask,
                spread_percent=spread_percent,
                threshold_percent=spread_percent_threshold,
                buys_count=len(buy_prices_desc),
                sells_count=len(sell_prices_asc),
            )
            return 0

        log_event(
            logger,
            "WARNING",
            "spread_threshold_breached",
            best_bid=best_bid,
            best_ask=best_ask,
            spread_percent=spread_percent,
            threshold_percent=spread_percent_threshold,
            buys_count=len(buy_prices_desc),
            sells_count=len(sell_prices_asc),
        )

        rc1, out1, err1 = kill_screen_session(session_name, timeout_s)
        if rc1 == 0:
            log_event(
                logger,
                "INFO",
                "screen_killed",
                session=session_name,
                rc=rc1,
                stdout=out1,
                stderr=err1,
            )
        else:
            log_event(
                logger,
                "ERROR",
                "screen_kill_failed",
                session=session_name,
                rc=rc1,
                stdout=out1,
                stderr=err1,
            )

        if rc1 == 0:
            rc2, out2, err2 = run_cancel_command(cancel_cmd, timeout_s)
            if rc2 == 0:
                log_event(
                    logger,
                    "INFO",
                    "cancel_command_ok",
                    rc=rc2,
                    stdout=out2,
                    stderr=err2,
                )
            else:
                log_event(
                    logger,
                    "ERROR",
                    "cancel_command_failed",
                    rc=rc2,
                    stdout=out2,
                    stderr=err2,
                )
        else:
            rc2 = None

        # Non-zero exit if any action failed
        status = 0 if (rc1 == 0 and rc2 == 0) else 2
        log_event(
            logger,
            "INFO" if status == 0 else "ERROR",
            "run_end",
            status=status,
        )
        return status
    except Exception:
        # Ensure no exception prevents next cron run
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

