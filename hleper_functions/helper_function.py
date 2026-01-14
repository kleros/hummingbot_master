import json
import os
import shlex
import subprocess
from typing import Any, Dict, Tuple


def atomic_write_state(state_path: str, data: Dict[str, Any]) -> None:
    full_path = os.path.expanduser(state_path)
    tmp_path = f"{full_path}.tmp"
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, full_path)


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
