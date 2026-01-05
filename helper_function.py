import json
import os
import shlex
import subprocess
from typing import Any, Dict, Optional, Tuple


def load_state(state_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def atomic_write_state(state_path: str, data: Dict[str, Any]) -> None:
    tmp_path = f"{state_path}.tmp"
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, state_path)


def determine_start_offset_by_last_line(log_file: str, last_line: Optional[str]) -> int:
    """
    Determine the resume offset by locating the last processed log line.
    - If last_line is None or not found (e.g., file rotated), start from 0.
    - If found, resume after that line.
    """
    if not last_line:
        return 0
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            # Iterate line by line; when we encounter last_line, return the offset just after it.
            for line in f:
                if line == last_line:
                    return f.tell()
        # Not found -> likely rotated/new file
        return 0
    except FileNotFoundError:
        return 0
    except Exception:
        return 0


def scan_new_lines(
    log_file: str, start_offset: int, levels: list[str]
) -> Tuple[int, bool, str]:
    matched = False
    new_offset = start_offset
    last_line_read = ""
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        f.seek(start_offset, os.SEEK_SET)
        for line in f:
            last_line_read = line
            if not matched:
                up = line.upper()
                for lvl in levels:
                    if lvl in up:
                        matched = True
                        break
        new_offset = f.tell()
    return new_offset, matched, last_line_read


def kill_screen_session(session_name: str, timeout_s: int) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["screen", "-S", session_name, "-X", "quit"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            check=False,
            text=True,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "screen command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "screen quit command timed out"
    except Exception as e:
        return 1, "", str(e)


def run_cancel_command(cmd: str, timeout_s: int) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            check=False,
            text=True,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "cancel command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "cancel command timed out"
    except Exception as e:
        return 1, "", str(e)


