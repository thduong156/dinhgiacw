"""
Quản lý lưu/tải portfolio CW dưới dạng JSON.
Module thuần Python — không phụ thuộc Streamlit.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# Thư mục lưu portfolio
PORTFOLIO_DIR = Path(__file__).parent / "portfolios"
DEFAULT_PORTFOLIO = "default"


def ensure_portfolio_dir():
    """Tạo thư mục portfolios nếu chưa có."""
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


def list_portfolios() -> list:
    """Trả về danh sách tên portfolio đã lưu (không có .json)."""
    ensure_portfolio_dir()
    files = sorted(PORTFOLIO_DIR.glob("*.json"))
    return [f.stem for f in files]


def save_portfolio(
    portfolio_name: str,
    cw_list: list,
    filename: Optional[str] = None,
) -> str:
    """
    Lưu portfolio ra file JSON.
    Returns filepath đã ghi.
    """
    ensure_portfolio_dir()

    if filename is None:
        safe_name = "".join(
            c if c.isalnum() or c in ("-", "_") else "_"
            for c in portfolio_name
        )
        filename = safe_name or "portfolio"

    filepath = PORTFOLIO_DIR / f"{filename}.json"

    data = {
        "portfolio_name": portfolio_name,
        "last_modified": datetime.now().isoformat(),
        "cw_list": [_serialize_cw(cw) for cw in cw_list],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return str(filepath)


def load_portfolio(filename: str) -> Optional[dict]:
    """
    Đọc portfolio từ file JSON.
    Returns dict {portfolio_name, last_modified, cw_list} hoặc None.
    Tự động migrate JSON cũ có primary_cw.
    """
    filepath = PORTFOLIO_DIR / f"{filename}.json"
    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None

    # Migration: JSON cũ có primary_cw → merge vào cw_list
    if "primary_cw" in data and data["primary_cw"]:
        old_primary = data["primary_cw"]
        old_list = data.get("cw_list", [])
        data["cw_list"] = [old_primary] + old_list
        del data["primary_cw"]

    return data


def delete_portfolio(filename: str) -> bool:
    """Xoá file portfolio. Returns True nếu xoá thành công."""
    filepath = PORTFOLIO_DIR / f"{filename}.json"
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def _serialize_cw(cw: dict) -> dict:
    """Chuyển cw_entry thành dict an toàn cho JSON. Bỏ key nội bộ (_source)."""
    result = {}
    for key, val in cw.items():
        if key.startswith("_"):
            continue
        if isinstance(val, date):
            result[key] = val.strftime("%d/%m/%Y")
        else:
            result[key] = val
    return result


def deserialize_cw_entry(data: dict) -> dict:
    """
    Chuyển JSON dict thành cw_entry runtime.
    Tính lại T và days_remaining từ maturity_date (vì thời gian đã trôi qua).
    """
    result = dict(data)

    # Parse maturity_date nếu là string
    mat_str = result.get("maturity_date", "")
    if isinstance(mat_str, str) and mat_str:
        try:
            mat_date = datetime.strptime(mat_str, "%d/%m/%Y").date()
            days = max((mat_date - date.today()).days, 0)
            result["T"] = max(days / 365.0, 0.001)
            result["days_remaining"] = days
            result["maturity_date"] = mat_date
        except ValueError:
            pass

    # Đảm bảo T luôn tồn tại
    if "T" not in result:
        result["T"] = result.get("days_remaining", 180) / 365.0
    if "days_remaining" not in result:
        result["days_remaining"] = max(int(result.get("T", 0.5) * 365), 0)

    # Đảm bảo q (dividend yield) luôn tồn tại
    result.setdefault("q", 0.0)

    return result
