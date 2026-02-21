"""
Scoring module cho Chứng Quyền.
Dùng chung bởi tab_recommend và daily_tracker.

Chấm điểm CW từ 0-100 dựa trên 7 tiêu chí:
  1. Định giá  (20đ) — Discount tốt, Premium xấu
  2. Đòn bẩy   (15đ) — Sweet spot 3-8x
  3. Delta     (15đ) — |Delta| càng cao càng nhạy
  4. Thời gian (15đ) — Càng dài càng tốt
  5. Hoà vốn  (10đ) — Càng gần càng tốt
  6. Moneyness (10đ) — ITM > ATM > OTM
  7. Theta Eff (15đ) — Time value / |theta|: bao nhiêu ngày theta cover
"""


def score_cw(analysis: dict, days_remaining: int) -> tuple:
    """
    Chấm điểm CW từ 0-100 dựa trên 7 tiêu chí cốt lõi.
    Trả về (total_score, breakdown_dict).
    """
    scores = {}

    # 1) Định giá hợp lý (20 điểm) — Discount tốt, Premium xấu
    pd_pct = analysis["premium_discount"]["percentage"]
    if pd_pct <= -10:
        scores["Định giá"] = 20
    elif pd_pct <= -3:
        scores["Định giá"] = 16
    elif pd_pct <= 3:
        scores["Định giá"] = 12
    elif pd_pct <= 10:
        scores["Định giá"] = 6
    elif pd_pct <= 20:
        scores["Định giá"] = 2
    else:
        scores["Định giá"] = 0

    # 2) Đòn bẩy hiệu dụng (15 điểm) — Sweet spot 3-8x
    eff_lev = analysis["effective_leverage"]
    if 5 <= eff_lev <= 8:
        scores["Đòn bẩy"] = 15
    elif 3 <= eff_lev < 5:
        scores["Đòn bẩy"] = 12
    elif 8 < eff_lev <= 12:
        scores["Đòn bẩy"] = 9
    elif 2 <= eff_lev < 3:
        scores["Đòn bẩy"] = 6
    elif eff_lev > 12:
        scores["Đòn bẩy"] = 4
    else:
        scores["Đòn bẩy"] = 2

    # 3) Delta (15 điểm) — |Delta| càng cao càng nhạy
    delta_abs = abs(analysis["greeks"]["delta"])
    if delta_abs >= 0.5:
        scores["Delta"] = 15
    elif delta_abs >= 0.35:
        scores["Delta"] = 12
    elif delta_abs >= 0.2:
        scores["Delta"] = 8
    elif delta_abs >= 0.1:
        scores["Delta"] = 5
    else:
        scores["Delta"] = 2

    # 4) Thời gian còn lại (15 điểm)
    if days_remaining > 180:
        scores["Thời gian"] = 15
    elif days_remaining > 120:
        scores["Thời gian"] = 12
    elif days_remaining > 60:
        scores["Thời gian"] = 8
    elif days_remaining > 30:
        scores["Thời gian"] = 4
    else:
        scores["Thời gian"] = 1

    # 5) Break-even (10 điểm) — Càng gần càng tốt
    be_pct = abs(analysis["break_even_change_pct"])
    if be_pct <= 5:
        scores["Hoà vốn"] = 10
    elif be_pct <= 10:
        scores["Hoà vốn"] = 8
    elif be_pct <= 15:
        scores["Hoà vốn"] = 5
    elif be_pct <= 25:
        scores["Hoà vốn"] = 2
    else:
        scores["Hoà vốn"] = 0

    # 6) Moneyness (10 điểm)
    moneyness = analysis["moneyness"]
    if "ITM" in moneyness:
        scores["Moneyness"] = 10
    elif "ATM" in moneyness:
        scores["Moneyness"] = 8
    else:
        scores["Moneyness"] = 3

    # 7) Theta Efficiency (15 điểm) — time_value / |theta|
    # Bao nhiêu ngày theta cover được time value? Càng nhiều càng tốt
    theta_eff = analysis.get("theta_efficiency", 0)
    if theta_eff >= 120:
        scores["Theta Eff"] = 15
    elif theta_eff >= 80:
        scores["Theta Eff"] = 12
    elif theta_eff >= 50:
        scores["Theta Eff"] = 8
    elif theta_eff >= 25:
        scores["Theta Eff"] = 4
    else:
        scores["Theta Eff"] = 1

    total = sum(scores.values())
    return total, scores


def grade_label(score: int) -> tuple:
    """Nhãn xếp hạng theo điểm. Returns (label_text, color_hex)."""
    if score >= 80:
        return "⭐ Xuất Sắc", "#22C55E"
    elif score >= 65:
        return "🟢 Tốt", "#4ADE80"
    elif score >= 50:
        return "🟡 Trung Bình", "#F59E0B"
    elif score >= 35:
        return "🟠 Dưới TB", "#F97316"
    else:
        return "🔴 Kém", "#EF4444"
