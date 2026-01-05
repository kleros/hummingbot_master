import os
import sys
from typing import Any, Dict
from wide_logger import setup_logger, log_event
from helper_function import (
    load_state,
    atomic_write_state,
    determine_start_offset_by_last_line,
    scan_new_lines,
    kill_screen_session,
    run_cancel_command,
)


def get_env_config() -> Dict[str, Any]:
    log_file = os.environ.get("HB_LOG_FILE", "/var/log/hummingbot/latest.log")
    state_file = os.environ.get("HB_STATE_FILE", "/tmp/hb_log_monitor.state")
    event_log_file = os.environ.get("HB_EVENT_LOG_FILE", "/tmp/hb_log_monitor.log")
    screen_session = os.environ.get("HB_SCREEN_SESSION", "hummingbot")
    cancel_cmd = os.environ.get("HB_CANCEL_CMD", "bitfinex-maker-kit cancel --symbol tPNKUSD")
    levels = os.environ.get("HB_MATCH_LEVELS", "ERROR,WARNING")
    timeout_s = int(os.environ.get("HB_CMD_TIMEOUT", "60"))

    levels_clean = [lvl.strip().upper() for lvl in levels.split(",") if lvl.strip()]
    if not levels_clean:
        levels_clean = ["ERROR", "WARNING"]

    return {
        "log_file": log_file,
        "state_file": state_file,
        "event_log_file": event_log_file,
        "screen_session": screen_session,
        "cancel_cmd": cancel_cmd,
        "levels": levels_clean,
        "timeout_s": timeout_s,
    }

 


def main() -> int:
    cfg = get_env_config()
    log_file = cfg["log_file"]
    state_file = cfg["state_file"]
    event_log_file = cfg["event_log_file"]
    levels = cfg["levels"]
    timeout_s = cfg["timeout_s"]
    session_name = cfg["screen_session"]
    cancel_cmd = cfg["cancel_cmd"]
    print(cfg)
    try:
        logger = setup_logger(event_log_file)
        log_event(logger, "INFO", "run_start", log_file=log_file, state_file=state_file)
        prev_state = load_state(state_file)
        last_line_prev = prev_state.get("last_line") if isinstance(prev_state, dict) else None
        start_offset = determine_start_offset_by_last_line(log_file, last_line_prev)
        try:
            new_offset, matched, last_line_read = scan_new_lines(log_file, start_offset, levels)
        except Exception as e:
            log_event(logger, "ERROR", "read_failed", error=str(e), log_file=log_file)
            return 1

        # Persist new state (only last processed line)
        try:
            atomic_write_state(state_file, {"last_line": last_line_read})
        except Exception as e:
            log_event(logger, "WARNING", "state_write_failed", error=str(e), state_file=state_file)
            # Continue anyway

        if not matched:
            log_event(
                logger,
                "INFO",
                "no_alerts_in_new_lines",
                start_offset=start_offset,
                new_offset=new_offset,
            )
            return 0

        log_event(
            logger,
            "WARNING",
            "alerts_detected",
            start_offset=start_offset,
            new_offset=new_offset,
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

