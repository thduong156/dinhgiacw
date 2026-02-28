"""
Issuer Hedging Engine — Tính toán phòng ngừa rủi ro cho TCPH (Tổ Chức Phát Hành CW).

Công thức cốt lõi (theo quy định CW Việt Nam):
    P_T = |Delta_raw| × OI_T / k
    ΔpT% = (P_T - p_T) / P_T × 100
    Δstock = round(P_T - p_T)  → dương = mua, âm = bán

Trong đó:
    Delta_raw = delta của quyền chọn CHƯA chia CR ∈ [-1, 1]
                (call: dương, put: âm → luôn lấy abs để tính vị thế)
    OI_T      = số lượng CW đang lưu hành tại ngày T
    k (cr)    = tỷ lệ chuyển đổi

Module thuần Python — không phụ thuộc Streamlit.
"""

import numpy as np
from datetime import date, datetime, timedelta
from scipy.stats import norm

from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator


# ─────────────────────────────────────────────────────────────────
# Công thức cốt lõi
# ─────────────────────────────────────────────────────────────────

def compute_theoretical_position(delta_raw: float, oi: int, k: float) -> float:
    """
    Vị thế phòng ngừa lý thuyết: P_T = |delta_raw| × OI / k.

    Args:
        delta_raw : BS delta chưa điều chỉnh CR ∈ [-1, 1].
                    Call → dương, Put → âm. Abs được lấy nội bộ.
        oi        : Số lượng CW đang lưu hành (Outstanding Interest).
        k         : Tỷ lệ chuyển đổi (conversion ratio, cr).

    Returns:
        Số cổ phiếu cơ sở lý thuyết TCPH phải nắm giữ.

    Raises:
        ValueError: Nếu k <= 0.
    """
    if k <= 0:
        raise ValueError(f"Tỷ lệ chuyển đổi k phải > 0, nhận được: {k}")
    if oi <= 0:
        return 0.0
    return abs(delta_raw) * oi / k


def compute_deviation(p_theo: float, p_actual: float) -> float:
    """
    Độ lệch vị thế: ΔpT% = (P_T - p_T) / P_T × 100.

    Dương → TCPH đang nắm thiếu (cần mua thêm).
    Âm    → TCPH đang nắm thừa  (có thể bán bớt).

    Returns 0.0 nếu p_theo <= 0 (tránh chia cho 0).
    """
    if p_theo <= 0:
        return 0.0
    return (p_theo - p_actual) / p_theo * 100.0


def get_compliance_status(
    dev_pct: float,
    green_threshold: float = 10.0,
    yellow_threshold: float = 20.0,
) -> str:
    """
    Phân loại mức độ tuân thủ theo hệ thống đèn giao thông.

    Args:
        dev_pct          : Độ lệch % (output của compute_deviation).
        green_threshold  : Ngưỡng an toàn (mặc định 10%).
        yellow_threshold : Ngưỡng cảnh báo (mặc định 20%).

    Returns:
        "safe"    → |dev_pct| ≤ green_threshold
        "warning" → green_threshold < |dev_pct| ≤ yellow_threshold
        "danger"  → |dev_pct| > yellow_threshold
    """
    lo = min(abs(green_threshold), abs(yellow_threshold))
    hi = max(abs(green_threshold), abs(yellow_threshold))
    abs_dev = abs(dev_pct)

    if abs_dev <= lo:
        return "safe"
    elif abs_dev <= hi:
        return "warning"
    else:
        return "danger"


def compute_buy_sell(p_theo: float, p_actual: float) -> int:
    """
    Tín hiệu giao dịch cần thực hiện để tái cân bằng.

    Returns:
        int: Số CP cần giao dịch (đã làm tròn).
             Dương → cần mua thêm (đang thiếu hedge).
             Âm   → cần bán bớt (đang thừa hedge).
             0    → không cần điều chỉnh.
    """
    return round(p_theo - p_actual)


# ─────────────────────────────────────────────────────────────────
# Dự báo vị thế tương lai
# ─────────────────────────────────────────────────────────────────

def forecast_hedge_positions(
    S: float,
    K: float,
    r: float,
    sigma: float,
    q: float,
    option_type: str,
    cr: float,
    oi: int,
    maturity_date_str: str,
    from_date_str: str,
    days_ahead: int = 30,
) -> list:
    """
    Dự báo vị thế phòng ngừa bắt buộc P_T trong N ngày tới.

    Giả định OI và sigma cố định, T giảm 1 ngày mỗi bước.
    Delta thay đổi theo thời gian khi T tiến về 0 (theta decay).

    Args:
        S                : Giá cơ sở hiện tại.
        K                : Giá thực hiện.
        r                : Lãi suất phi rủi ro (decimal).
        sigma            : Biến động ngầm định (decimal, VD: 0.35).
        q                : Tỷ suất cổ tức (decimal).
        option_type      : "call" hoặc "put".
        cr               : Tỷ lệ chuyển đổi.
        oi               : Số CW lưu hành (giả định cố định).
        maturity_date_str: Ngày đáo hạn "DD/MM/YYYY".
        from_date_str    : Ngày bắt đầu dự báo "YYYY-MM-DD".
        days_ahead       : Số ngày dự báo (capped tại ngày đáo hạn).

    Returns:
        list[dict] với mỗi phần tử:
            {date, days_to_maturity, T, delta_raw, p_theo}
        Trả list rỗng nếu CW đã đáo hạn hoặc parse lỗi.
    """
    # Parse ngày đáo hạn
    try:
        mat_date = datetime.strptime(maturity_date_str, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return []

    # Parse ngày bắt đầu
    try:
        start_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        start_date = date.today()

    days_to_mat = (mat_date - start_date).days
    if days_to_mat <= 0:
        return []

    actual_days = min(days_ahead, days_to_mat)
    results = []

    for d in range(1, actual_days + 1):
        forecast_date = start_date + timedelta(days=d)
        days_left = (mat_date - forecast_date).days
        T = max(days_left / 365.0, 0.001)

        try:
            model = BlackScholesModel(S, K, T, r, sigma, option_type, q=q)
            calc  = GreeksCalculator(model, conversion_ratio=1.0)
            delta_raw = calc.delta_raw()   # CR=1 → delta() == delta_raw()
            p_theo    = compute_theoretical_position(delta_raw, oi, cr)
        except Exception:
            delta_raw = None
            p_theo    = None

        results.append({
            "date":             forecast_date.strftime("%Y-%m-%d"),
            "days_to_maturity": days_left,
            "T":                round(T, 6),
            "delta_raw":        round(delta_raw, 6) if delta_raw is not None else None,
            "p_theo":           round(p_theo, 2)    if p_theo    is not None else None,
        })

    return results
