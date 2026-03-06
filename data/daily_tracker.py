"""
Daily Data Tracker — Lưu/tải dữ liệu hàng ngày cho từng CW.

Mỗi CW lưu thành 1 file JSON trong data/daily_history/.
Mỗi record chứa: input hàng ngày (S, cw_price, sigma)
+ auto-calculated fields (theoretical_price, P/D%, Greeks, score...).

Module thuần Python — không phụ thuộc Streamlit.
"""

import json
import numpy as np
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.warrant import WarrantAnalyzer
from core.scoring import score_cw

# Thư mục lưu daily history
DAILY_HISTORY_DIR = Path(__file__).parent / "daily_history"


def ensure_history_dir():
    """Tạo thư mục daily_history nếu chưa có."""
    DAILY_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(ma_cw: str) -> str:
    """Chuyển mã CW thành filename an toàn (uppercase, strip special chars)."""
    clean = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in ma_cw.upper().strip()
    )
    return clean or "UNKNOWN"


def compute_auto_fields(cw_static: dict, daily_input: dict) -> dict:
    """
    Tính toán tự động tất cả derived fields từ WarrantAnalyzer.

    Args:
        cw_static: {K, cr, option_type, maturity_date (DD/MM/YYYY str), r}
        daily_input: {date (YYYY-MM-DD str), S, cw_price, sigma}

    Returns:
        Dict auto-calculated fields để merge vào record.

    LƯU Ý: T được tính relative to record date, không phải today.
    """
    # Parse dates
    record_date_str = daily_input.get("date", date.today().strftime("%Y-%m-%d"))
    record_date = datetime.strptime(record_date_str, "%Y-%m-%d").date()

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
    T_at_record = max(days_at_record / 365.0, 0.001)

    S = daily_input["S"]
    cw_price = daily_input["cw_price"]
    sigma = daily_input.get("sigma", cw_static.get("sigma", 0.30))

    try:
        analyzer = WarrantAnalyzer(
            S=S,
            K=cw_static["K"],
            T=T_at_record,
            r=cw_static.get("r", 0.03),
            sigma=sigma,
            cw_market_price=cw_price,
            conversion_ratio=cw_static["cr"],
            option_type=cw_static["option_type"],
            q=cw_static.get("q", 0.0),
        )
        analysis = analyzer.full_analysis()

        total_score, _ = score_cw(analysis, days_at_record)

        return {
            "theoretical_price": round(analysis["theoretical_price"], 2),
            "premium_discount_pct": round(analysis["premium_discount"]["percentage"], 2),
            "implied_volatility": (
                round(analysis["implied_volatility"], 4)
                if analysis["implied_volatility"] else None
            ),
            "delta": round(analysis["greeks"]["delta"], 6),
            "gamma": round(analysis["greeks"]["gamma"], 8),
            "theta": round(analysis["greeks"]["theta"], 4),
            "effective_leverage": round(analysis["effective_leverage"], 2),
            "moneyness": analysis["moneyness"],
            "intrinsic_value": round(analysis["intrinsic_value"], 2),
            "time_value": round(analysis["time_value"], 2),
            "break_even": round(analysis["break_even"], 2),
            "score": total_score,
        }
    except Exception:
        # Fallback nếu tính toán lỗi — vẫn lưu record nhưng không có auto fields
        return {
            "theoretical_price": None,
            "premium_discount_pct": None,
            "implied_volatility": None,
            "delta": None,
            "gamma": None,
            "theta": None,
            "effective_leverage": None,
            "moneyness": None,
            "intrinsic_value": None,
            "time_value": None,
            "break_even": None,
            "score": None,
        }


def save_daily_record(ma_cw: str, cw_static: dict, record: dict) -> str:
    """
    Upsert (thêm hoặc cập nhật) một daily record cho CW.

    Args:
        ma_cw: Mã CW (e.g. "CMWG2604")
        cw_static: {ma_co_so, K, cr, option_type, maturity_date, r}
        record: {date, S, cw_price, sigma, ...auto fields}

    Returns:
        Filepath đã ghi.
    """
    ensure_history_dir()
    filename = _safe_filename(ma_cw)
    filepath = DAILY_HISTORY_DIR / f"{filename}.json"

    # Load existing or create new
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # Serialize maturity_date
        mat = cw_static.get("maturity_date", "")
        if isinstance(mat, date):
            mat = mat.strftime("%d/%m/%Y")

        data = {
            "ma_cw": ma_cw.upper(),
            "ma_co_so": cw_static.get("ma_co_so", "N/A"),
            "K": cw_static.get("K", 0),
            "cr": cw_static.get("cr", 1),
            "option_type": cw_static.get("option_type", "call"),
            "maturity_date": mat,
            "r": cw_static.get("r", 0.03),
            "records": [],
        }

    # Update static info (in case it changed)
    mat = cw_static.get("maturity_date", data.get("maturity_date", ""))
    if isinstance(mat, date):
        mat = mat.strftime("%d/%m/%Y")
    data["ma_co_so"] = cw_static.get("ma_co_so", data.get("ma_co_so", "N/A"))
    data["K"] = cw_static.get("K", data.get("K", 0))
    data["cr"] = cw_static.get("cr", data.get("cr", 1))
    data["option_type"] = cw_static.get("option_type", data.get("option_type", "call"))
    data["maturity_date"] = mat
    data["r"] = cw_static.get("r", data.get("r", 0.03))

    # Upsert record by date
    record_date = record.get("date", date.today().strftime("%Y-%m-%d"))
    existing_dates = {r["date"]: i for i, r in enumerate(data["records"])}

    if record_date in existing_dates:
        # Overwrite existing record for same date
        data["records"][existing_dates[record_date]] = record
    else:
        data["records"].append(record)

    # Sort records by date ascending
    data["records"].sort(key=lambda r: r.get("date", ""))

    # Write
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return str(filepath)


def load_daily_history(ma_cw: str) -> Optional[dict]:
    """Load full history cho 1 CW. Returns None nếu không có file."""
    ensure_history_dir()
    filename = _safe_filename(ma_cw)
    filepath = DAILY_HISTORY_DIR / f"{filename}.json"

    if not filepath.exists():
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_tracked_cw() -> list:
    """Scan daily_history/*.json → return list mã CW (uppercase)."""
    ensure_history_dir()
    result = []
    for f in sorted(DAILY_HISTORY_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                result.append(data.get("ma_cw", f.stem))
        except (json.JSONDecodeError, KeyError):
            result.append(f.stem)
    return result


def get_latest_record(ma_cw: str) -> Optional[dict]:
    """Return record cuối cùng (ngày gần nhất) cho 1 CW."""
    data = load_daily_history(ma_cw)
    if data and data.get("records"):
        return data["records"][-1]
    return None


def delete_daily_record(ma_cw: str, date_str: str) -> bool:
    """Xóa 1 record theo date. Returns True nếu thành công."""
    ensure_history_dir()
    filename = _safe_filename(ma_cw)
    filepath = DAILY_HISTORY_DIR / f"{filename}.json"

    if not filepath.exists():
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    original_len = len(data.get("records", []))
    data["records"] = [r for r in data.get("records", []) if r.get("date") != date_str]

    if len(data["records"]) == original_len:
        return False  # Không tìm thấy record

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return True


def delete_all_history(ma_cw: str) -> bool:
    """Xóa toàn bộ history file cho 1 CW."""
    ensure_history_dir()
    filename = _safe_filename(ma_cw)
    filepath = DAILY_HISTORY_DIR / f"{filename}.json"

    if filepath.exists():
        filepath.unlink()
        return True
    return False


def rename_daily_history(old_ma_cw: str, new_ma_cw: str) -> bool:
    """Đổi tên file history khi mã CW thay đổi. Returns True nếu thành công."""
    ensure_history_dir()
    old_file = DAILY_HISTORY_DIR / f"{_safe_filename(old_ma_cw)}.json"
    new_file = DAILY_HISTORY_DIR / f"{_safe_filename(new_ma_cw)}.json"
    if old_file.exists() and old_file != new_file:
        old_file.rename(new_file)
        return True
    return False


def get_history_dataframe(ma_cw: str) -> Optional[pd.DataFrame]:
    """Load records vào pandas DataFrame. Returns None nếu không có data."""
    data = load_daily_history(ma_cw)
    if not data or not data.get("records"):
        return None

    df = pd.DataFrame(data["records"])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=True).reset_index(drop=True)
    return df


def export_history_csv(ma_cw: str) -> Optional[str]:
    """Export history thành CSV string (cho st.download_button). Returns None nếu không có data."""
    df = get_history_dataframe(ma_cw)
    if df is None:
        return None
    return df.to_csv(index=False)


def compute_daily_returns(ma_cw: str, price_field: str = "cw_price") -> Optional[np.ndarray]:
    """
    Tính daily returns từ price field.
    r[i] = (price[i] - price[i-1]) / price[i-1]

    Dùng cho Markowitz enhancement.
    Returns None nếu < 2 data points.
    """
    df = get_history_dataframe(ma_cw)
    if df is None or len(df) < 2:
        return None

    if price_field not in df.columns:
        return None

    prices = df[price_field].dropna().values
    if len(prices) < 2:
        return None

    # Filter out zero/negative prices
    valid = prices[prices > 0]
    if len(valid) < 2:
        return None

    returns = np.diff(valid) / valid[:-1]
    return returns


def compute_daily_spot_returns(ma_cw: str) -> Optional[np.ndarray]:
    """Tính daily returns từ S (spot price). Dùng cho correlation."""
    return compute_daily_returns(ma_cw, price_field="S")
