import re
import shlex
import subprocess
from typing import List, Optional, Tuple


def run_list_command(cmd: str, timeout_s: int) -> Tuple[int, str, str]:
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
        return 127, "", "list command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "list command timed out"
    except Exception as e:
        return 1, "", str(e)


_ROW_RE = re.compile(
    r"^\s*(\d+)\s+([A-Z ]+?)\s+(BUY|SELL)\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?)\s+\d{4}-\d{2}-\d{2}\s",
    re.IGNORECASE,
)


def parse_orders_from_text(text: str) -> List[dict]:
    orders: List[dict] = []
    for raw in text.splitlines():
        m = _ROW_RE.match(raw)
        if not m:
            continue
        # id_str = m.group(1)  # not used presently
        # type_str = m.group(2)  # not used presently
        side = m.group(3).upper()
        amount = float(m.group(4))
        price = float(m.group(5))
        orders.append({"side": side, "amount": amount, "price": price})
    return orders


def split_filter_sort_orders(orders: List[dict], min_amount: float) -> Tuple[List[float], List[float]]:
    buys: List[float] = []
    sells: List[float] = []
    for o in orders:
        if o["amount"] < min_amount:
            continue
        if o["side"] == "BUY":
            buys.append(o["price"])
        elif o["side"] == "SELL":
            sells.append(o["price"])
    buys.sort(reverse=True)
    sells.sort()
    return buys, sells


def compute_spread_percent_mid(best_bid: Optional[float], best_ask: Optional[float]) -> Optional[float]:
    if best_bid is None or best_ask is None:
        return None
    if best_ask <= 0 or best_bid <= 0:
        return None
    mid = (best_ask + best_bid) / 2.0
    if mid <= 0:
        return None
    return ((best_ask - best_bid) / mid) * 100.0


