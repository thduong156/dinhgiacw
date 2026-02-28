"""
Issuer Hedge Tracker — Lưu/tải dữ liệu phòng ngừa rủi ro cho TCPH.

Mỗi CW lưu thành 1 file JSON trong data/issuer_hedge_history/.
Cấu trúc JSON:
{
  "ma_cw": "CWXXX",
  "K": 100000, "cr": 1, "option_type": "call",
  "maturity_date": "DD/MM/YYYY", "r": 0.03, "q": 0.0,
  "records": [
    {
      "date": "YYYY-MM-DD",
      "oi": 500000,        "p_actual": 250000,
      "S": 100000.0,       "sigma": 0.35,
      "delta_raw": 0.62,   "p_theo": 310000.0,
      "deviation_pct": 19.3548, "buy_sell": 60000,
      "status": "warning"
    }
  ]
}

Module thuần Python — không phụ thuộc Streamlit.
"""

import json
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from core.issuer_hedging import (
    compute_theoretical_position,
    compute_deviation,
    get_compliance_status,
    compute_buy_sell,
)

# Thư mục lưu hedge history
HEDGE_HISTORY_DIR = Path(__file__).parent / "issuer_hedge_history"


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def ensure_history_dir() -> None:
    """Tạo thư mục issuer_hedge_history nếu chưa có."""
    HEDGE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(ma_cw: str) -> str:
    """Chuyển mã CW thành filename an toàn (uppercase, strip special chars)."""
    clean = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in ma_cw.upper().strip()
    )
    return clean or "UNKNOWN"


def _hedge_filepath(ma_cw: str) -> Path:
    ensure_history_dir()
    return HEDGE_HISTORY_DIR / f"{_safe_filename(ma_cw)}.json"


# ─────────────────────────────────────────────────────────────────
# Auto-calculation
# ─────────────────────────────────────────────────────────────────

def compute_hedge_fields(cw_static: dict, record_input: dict) -> dict:
    """
    Tính tự động delta_raw, p_theo, deviation_pct, buy_sell, status.

    Args:
        cw_static    : {K, cr, option_type, maturity_date (DD/MM/YYYY), r, q (opt)}
        record_input : {date (YYYY-MM-DD), S, sigma (decimal), oi (int), p_actual}

    Returns:
        Dict với các auto-computed fields:
        {delta_raw, p_theo, deviation_pct, buy_sell, status}

    LƯU Ý: T được tính relative to record date, không phải today —
            giống compute_auto_fields() trong daily_tracker.py.
    Sử dụng default threshold 10%/20% — UI sẽ override status nếu cần.
    """
    # Parse record date
    record_date_str = record_input.get("date", date.today().strftime("%Y-%m-%d"))
    try:
        record_date = datetime.strptime(record_date_str, "%Y-%m-%d").date()
    except ValueError:
        record_date = date.today()

    # Parse maturity_date (DD/MM/YYYY)
    mat_str = cw_static.get("maturity_date", "")
    if isinstance(mat_str, date):
        mat_date = mat_str
    elif isinstance(mat_str, str) and mat_str:
        try:
            mat_date = datetime.strptime(mat_str, "%d/%m/%Y").date()
        except ValueError:
            mat_date = record_date
    else:
        mat_date = record_date

    days_at_record = max((mat_date - record_date).days, 0)
    T = max(days_at_record / 365.0, 0.001)

    # Parse record fields
    try:
        S         = float(record_input["S"])
        sigma     = float(record_input["sigma"])   # decimal
        oi        = int(record_input["oi"])
        p_actual  = float(record_input["p_actual"])
        K         = float(cw_static["K"])
        cr        = float(cw_static["cr"])
        r         = float(cw_static.get("r", 0.03))
        q         = float(cw_static.get("q", 0.0))
        opt_type  = cw_static.get("option_type", "call")
    except (KeyError, TypeError, ValueError):
        return {
            "delta_raw": None, "p_theo": None,
            "deviation_pct": None, "buy_sell": None, "status": "error",
        }

    try:
        model      = BlackScholesModel(S, K, T, r, sigma, opt_type, q=q)
        calc       = GreeksCalculator(model, conversion_ratio=1.0)
        delta_raw  = calc.delta_raw()   # CR=1 → equals raw N(d1)·e^{-qT}

        p_theo        = compute_theoretical_position(delta_raw, oi, cr)
        deviation_pct = compute_deviation(p_theo, p_actual)
        buy_sell      = compute_buy_sell(p_theo, p_actual)
        status        = get_compliance_status(deviation_pct)   # default 10/20

        return {
            "delta_raw":     round(delta_raw,     6),
            "p_theo":        round(p_theo,         2),
            "deviation_pct": round(deviation_pct,  4),
            "buy_sell":      buy_sell,
            "status":        status,
        }
    except Exception:
        return {
            "delta_raw": None, "p_theo": None,
            "deviation_pct": None, "buy_sell": None, "status": "error",
        }


# ─────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────

def save_hedge_record(ma_cw: str, cw_static: dict, record: dict) -> str:
    """
    Upsert một hedge record (upsert by date, sort ascending).

    Args:
        ma_cw     : Mã CW (e.g. "CMWG2604").
        cw_static : {K, cr, option_type, maturity_date, r, q}.
        record    : Record đã merged (record_input + compute_hedge_fields output).
                    Must contain "date" key in YYYY-MM-DD format.

    Returns:
        Filepath đã ghi.
    """
    fpath = _hedge_filepath(ma_cw)

    # Load existing data hoặc khởi tạo mới
    if fpath.exists():
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        mat_str = cw_static.get("maturity_date", "")
        if isinstance(mat_str, date):
            mat_str = mat_str.strftime("%d/%m/%Y")
        data = {
            "ma_cw":         ma_cw.upper(),
            "K":             float(cw_static.get("K", 0)),
            "cr":            float(cw_static.get("cr", 1)),
            "option_type":   cw_static.get("option_type", "call"),
            "maturity_date": mat_str,
            "r":             float(cw_static.get("r", 0.03)),
            "q":             float(cw_static.get("q", 0.0)),
            "records":       [],
        }

    # Cập nhật metadata static
    mat_str = cw_static.get("maturity_date", data.get("maturity_date", ""))
    if isinstance(mat_str, date):
        mat_str = mat_str.strftime("%d/%m/%Y")
    data["K"]             = float(cw_static.get("K", data.get("K", 0)))
    data["cr"]            = float(cw_static.get("cr", data.get("cr", 1)))
    data["option_type"]   = cw_static.get("option_type", data.get("option_type", "call"))
    data["maturity_date"] = mat_str
    data["r"]             = float(cw_static.get("r", data.get("r", 0.03)))
    data["q"]             = float(cw_static.get("q", data.get("q", 0.0)))

    # Upsert by date
    record_date = record.get("date", "")
    records = data.get("records", [])
    updated = False
    for i, r in enumerate(records):
        if r.get("date") == record_date:
            records[i] = record
            updated = True
            break
    if not updated:
        records.append(record)

    # Sort ascending by date
    records.sort(key=lambda r: r.get("date", ""))
    data["records"] = records

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return str(fpath)


def load_hedge_history(ma_cw: str) -> Optional[dict]:
    """Load full history cho 1 CW. Returns None nếu chưa có file."""
    fpath = _hedge_filepath(ma_cw)
    if not fpath.exists():
        return None
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_all_tracked_cw_hedge() -> list:
    """Scan issuer_hedge_history/*.json → return list mã CW (uppercase)."""
    ensure_history_dir()
    results = []
    for fpath in HEDGE_HISTORY_DIR.glob("*.json"):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            ma = data.get("ma_cw", fpath.stem).upper()
            results.append(ma)
        except Exception:
            results.append(fpath.stem.upper())
    return sorted(results)


def get_hedge_dataframe(ma_cw: str) -> Optional[pd.DataFrame]:
    """
    Load records vào pandas DataFrame, sort ascending by date.

    Returns None nếu không có data.
    Column "date" là datetime64, các cột số được coerce về float/int.
    """
    data = load_hedge_history(ma_cw)
    if not data or not data.get("records"):
        return None

    df = pd.DataFrame(data["records"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    # Đảm bảo kiểu dữ liệu số
    for col in ["oi", "p_actual", "p_theo", "deviation_pct",
                "delta_raw", "S", "sigma", "buy_sell"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "oi" in df.columns:
        df["oi"] = df["oi"].fillna(0).astype("int64")
    if "buy_sell" in df.columns:
        df["buy_sell"] = df["buy_sell"].fillna(0).astype("int64")

    return df


def get_latest_hedge_record(ma_cw: str) -> Optional[dict]:
    """Return record cuối cùng (ngày gần nhất) cho 1 CW."""
    data = load_hedge_history(ma_cw)
    if not data or not data.get("records"):
        return None
    return data["records"][-1]   # đã sort ascending khi save


def export_hedge_csv(ma_cw: str) -> Optional[str]:
    """Export history thành CSV string cho st.download_button. Returns None nếu rỗng."""
    df = get_hedge_dataframe(ma_cw)
    if df is None or df.empty:
        return None
    return df.to_csv(index=False)


def delete_hedge_record(ma_cw: str, date_str: str) -> bool:
    """
    Xóa 1 record theo date (YYYY-MM-DD). Returns True nếu thành công.
    """
    fpath = _hedge_filepath(ma_cw)
    if not fpath.exists():
        return False
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        original_len = len(data.get("records", []))
        data["records"] = [
            r for r in data.get("records", [])
            if r.get("date") != date_str
        ]
        if len(data["records"]) == original_len:
            return False
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def delete_all_hedge_history(ma_cw: str) -> bool:
    """Xóa toàn bộ file JSON lịch sử cho 1 CW. Returns True nếu thành công."""
    fpath = _hedge_filepath(ma_cw)
    if not fpath.exists():
        return False
    try:
        fpath.unlink()
        return True
    except Exception:
        return False
