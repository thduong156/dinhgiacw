import streamlit as st
import numpy as np
import pandas as pd
from core.warrant import WarrantAnalyzer
from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import (
    create_pnl_heatmap,
    create_breakeven_decay_chart,
    create_vol_shock_heatmap,
)


def render_scenario_tab(cw):
    """Tab 9: Kịch Bản & Kiểm Tra Sức Chịu Đựng."""
    if cw is None:
        tab_empty_state(
            "🎯", "Chưa chọn CW để phân tích kịch bản",
            "Thêm CW vào danh mục ở thanh bên, sau đó chọn CW để xem "
            "phân tích kịch bản và kiểm tra sức chịu đựng.",
            "Thanh bên → Chọn CW",
        )
        return

    section_title("🎯", "Kịch Bản & Kiểm Tra Sức Chịu Đựng")

    st.markdown(
        '<div class="info-box">'
        '<b>Phân tích kịch bản giúp trả lời 3 câu hỏi then chốt:</b><br>'
        '1. <b>Nên mua CW nào?</b> → Xem lãi/lỗ ở nhiều mức giá<br>'
        '2. <b>Khi nào vào lệnh?</b> → Xem ảnh hưởng của cú sốc biến động<br>'
        '3. <b>Khi nào thoát lệnh?</b> → Xem đường suy giảm hoà vốn & bào mòn thời gian'
        '</div>',
        unsafe_allow_html=True,
    )

    # Xây dựng bộ phân tích
    analyzer = WarrantAnalyzer(
        S=cw["S"], K=cw["K"], T=cw["T"],
        r=cw["r"], sigma=cw["sigma"],
        cw_market_price=cw["cw_price"],
        conversion_ratio=cw["cr"],
        option_type=cw["option_type"],
        q=cw.get("q", 0.0),
    )

    # Hiển thị toàn bộ 6 phần phân tích
    _render_pnl_heatmap(analyzer, cw)
    section_divider()
    _render_vol_shock(analyzer, cw)
    section_divider()
    _render_quick_scenarios(analyzer, cw)
    section_divider()
    _render_breakeven_decay(analyzer, cw)
    section_divider()
    _render_holding_analysis(analyzer, cw)
    section_divider()
    _render_custom_scenario(analyzer, cw)


# ============================================================
# 1. BẢNG NHIỆT LÃI/LỖ (Giá × Thời Gian) — Tính năng chính
# ============================================================

def _render_pnl_heatmap(analyzer, cw):
    """Bảng nhiệt Lãi/Lỗ: Y = Giá cơ sở, X = Ngày còn lại."""
    section_title("📊", "Bảng Nhiệt Lãi/Lỗ (Giá × Thời Gian)")

    S = cw["S"]
    cw_price = cw["cw_price"]
    cr = cw["cr"]
    max_days = int(cw["T"] * 365)
    if max_days < 2:
        max_days = 2

    # Phạm vi giá: +-25% từ giá hiện tại, 11 bước
    pct_range = np.linspace(-0.25, 0.25, 11)
    price_levels = [S * (1 + p) for p in pct_range]
    price_labels = [f"{p:,.0f}" for p in price_levels]

    # Phạm vi thời gian: từ max_days đến 1, ~12 bước
    num_time_steps = min(12, max_days)
    time_steps = np.linspace(max_days, 1, num_time_steps, dtype=int).tolist()
    # Loại bỏ trùng lặp và sắp xếp giảm dần
    time_steps = sorted(set(time_steps), reverse=True)
    time_labels = [f"{d} ngày" for d in time_steps]

    # Tính toán lưới lãi/lỗ
    z_data = []
    be_y = []  # giá hoà vốn tại mỗi bước thời gian

    for s_new in price_levels:
        row = []
        for days in time_steps:
            T_new = max(days / 365.0, 0.001)
            model = BlackScholesModel(
                s_new, cw["K"], T_new, cw["r"], cw["sigma"],
                cw["option_type"], q=cw.get("q", 0.0),
            )
            cw_new = model.price() / cr
            pnl = cw_new - cw_price

            # Nhân theo số lượng nếu có vị thế
            qty = cw.get("quantity")
            entry_p = cw.get("entry_price")
            if qty and entry_p and qty > 0 and entry_p > 0:
                pnl = (cw_new - entry_p) * qty
            row.append(round(pnl))
        z_data.append(row)

    # Giá hoà vốn tại mỗi bước thời gian
    for days in time_steps:
        T_new = max(days / 365.0, 0.001)
        ref_price = cw.get("entry_price") if (cw.get("entry_price") or 0) > 0 else cw_price
        # Tìm kiếm nhị phân giá hoà vốn
        be = _find_breakeven_price(
            cw["K"], T_new, cw["r"], cw["sigma"], cr,
            cw["option_type"], cw.get("q", 0.0), ref_price, S,
        )
        be_y.append(f"{be:,.0f}")

    # Đánh dấu vị trí hiện tại
    current_marker = None
    current_days_left = max_days
    if time_steps:
        closest_t = min(time_steps, key=lambda d: abs(d - current_days_left))
        current_marker = (f"{closest_t} ngày", f"{S:,.0f}")

    chart_container("Bảng Nhiệt Lãi/Lỗ: Giá Cổ Sở × Ngày Còn Lại")
    fig = create_pnl_heatmap(z_data, price_labels, time_labels, be_y, current_marker)
    st.plotly_chart(fig, use_container_width=True)
    chart_container_end()

    # Giải thích
    has_position = (
        cw.get("quantity") and cw.get("entry_price")
        and cw["quantity"] > 0 and cw["entry_price"] > 0
    )
    if has_position:
        st.markdown(
            f'<div class="info-box">'
            f'Lãi/Lỗ tính cho vị thế: <b>{cw["quantity"]:,} CW</b> × '
            f'giá vào <b>{format_vnd(cw["entry_price"])} đ</b>. '
            f'Đường vàng = điểm hoà vốn. Kim cương cam = vị trí hiện tại.'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="info-box">'
            'Lãi/Lỗ = (Giá CW mới − Giá CW hiện tại) trên <b>1 CW</b>. '
            'Thêm <b>Giá vào & Cắt lỗ</b> ở thanh bên để tính lãi/lỗ theo vị thế thực.'
            '</div>',
            unsafe_allow_html=True,
        )


def _find_breakeven_price(K, T, r, sigma, cr, option_type, q, target_price, S_guess):
    """Tìm kiếm nhị phân giá cơ sở hoà vốn tại thời điểm T cho trước."""
    low = K * 0.3
    high = K * 3.0
    for _ in range(60):
        mid = (low + high) / 2
        model = BlackScholesModel(mid, K, T, r, sigma, option_type, q=q)
        cw_p = model.price() / cr
        if cw_p < target_price:
            if option_type == "call":
                low = mid
            else:
                high = mid
        else:
            if option_type == "call":
                high = mid
            else:
                low = mid
        if abs(cw_p - target_price) < 0.01:
            break
    return round((low + high) / 2)


# ============================================================
# 2. PHÂN TÍCH CÚ SỐC BIẾN ĐỘNG
# ============================================================

def _render_vol_shock(analyzer, cw):
    """Bảng nhiệt: Y = Thay đổi giá CS (%), X = Thay đổi IV (điểm)."""
    section_title("💥", "Phân Tích Cú Sốc Biến Động")

    S = cw["S"]
    cw_price = cw["cw_price"]
    cr = cw["cr"]
    max_days = max(int(cw["T"] * 365), 2)

    # Thanh trượt thời gian nắm giữ
    slider_max = min(max_days - 1, 60)
    hold_days = st.slider(
        "Thời gian nắm giữ (ngày)",
        min_value=1,
        max_value=max(slider_max, 1),
        value=min(5, max(slider_max, 1)),
        step=1,
        key="vol_shock_hold_days",
    )

    T_hold = max((cw["T"] * 365 - hold_days) / 365.0, 0.001)

    # Phạm vi thay đổi giá
    price_pcts = [-15, -10, -7, -5, -3, 0, 3, 5, 7, 10, 15]
    price_labels = [f"{p:+d}%" for p in price_pcts]

    # Phạm vi thay đổi IV (điểm tuyệt đối)
    iv_points = [-10, -7, -5, -3, 0, 3, 5, 7, 10]
    iv_labels = [f"{v:+d} điểm" for v in iv_points]

    # Tính toán lưới lãi/lỗ
    z_data = []
    for dp in price_pcts:
        row = []
        for dv in iv_points:
            new_S = S * (1 + dp / 100.0)
            new_sigma = cw["sigma"] + dv / 100.0
            if new_sigma <= 0.01:
                new_sigma = 0.01

            model = BlackScholesModel(
                new_S, cw["K"], T_hold, cw["r"], new_sigma,
                cw["option_type"], q=cw.get("q", 0.0),
            )
            cw_new = model.price() / cr
            pnl = cw_new - cw_price

            qty = cw.get("quantity")
            entry_p = cw.get("entry_price")
            if qty and entry_p and qty > 0 and entry_p > 0:
                pnl = (cw_new - entry_p) * qty
            row.append(round(pnl))
        z_data.append(row)

    chart_container(f"Cú Sốc Biến Động: Nắm giữ {hold_days} ngày")
    fig = create_vol_shock_heatmap(z_data, price_labels, iv_labels)
    st.plotly_chart(fig, use_container_width=True)
    chart_container_end()

    st.markdown(
        f'<div class="info-box">'
        f'Cách đọc bảng nhiệt: "Nếu cơ sở giảm 5% <b>VÀ</b> biến động ngầm định tăng 5 điểm '
        f'sau <b>{hold_days} ngày</b> → CW sẽ lãi/lỗ bao nhiêu?"<br>'
        f'<small>Thời gian còn lại sau kịch bản: {T_hold*365:.0f} ngày '
        f'(từ {cw["T"]*365:.0f} ngày hiện tại)</small>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 3. 5 KỊCH BẢN NHANH (thiết lập sẵn)
# ============================================================

def _render_quick_scenarios(analyzer, cw):
    """5 kịch bản thiết lập sẵn: Tăng, Giảm, Sụp đổ, Bào mòn thời gian, Tăng mạnh + Biến động giảm."""
    section_title("⚡", "5 Kịch Bản Nhanh")

    S = cw["S"]
    K = cw["K"]
    T_days = cw["T"] * 365
    cr = cw["cr"]
    sigma = cw["sigma"]
    cw_price = cw["cw_price"]

    scenarios = [
        {
            "name": "🐂 Tăng giá",
            "desc": "Cơ sở +5%, biến động ổn định",
            "dS_pct": 5, "dIV_pts": 0, "hold_days": 5,
            "color": "#22C55E",
        },
        {
            "name": "🐻 Giảm giá",
            "desc": "Cơ sở -5%, biến động +3 điểm",
            "dS_pct": -5, "dIV_pts": 3, "hold_days": 5,
            "color": "#EF4444",
        },
        {
            "name": "💥 Sụp đổ",
            "desc": "Cơ sở -10%, biến động +8 điểm",
            "dS_pct": -10, "dIV_pts": 8, "hold_days": 3,
            "color": "#B91C1C",
        },
        {
            "name": "⏳ Bào mòn thời gian",
            "desc": "Cơ sở đi ngang, 10 ngày trôi qua",
            "dS_pct": 0, "dIV_pts": 0, "hold_days": 10,
            "color": "#F59E0B",
        },
        {
            "name": "🚀 Tăng mạnh + BĐ giảm",
            "desc": "Cơ sở +8%, biến động -5 điểm",
            "dS_pct": 8, "dIV_pts": -5, "hold_days": 5,
            "color": "#3B82F6",
        },
    ]

    cols = st.columns(5)

    for idx, sc in enumerate(scenarios):
        with cols[idx]:
            new_S = S * (1 + sc["dS_pct"] / 100.0)
            new_sigma = max(sigma + sc["dIV_pts"] / 100.0, 0.01)
            T_new = max((T_days - sc["hold_days"]) / 365.0, 0.001)

            model = BlackScholesModel(
                new_S, K, T_new, cw["r"], new_sigma,
                cw["option_type"], q=cw.get("q", 0.0),
            )
            cw_new = model.price() / cr

            # Chỉ số Hy Lạp tại điểm mới
            greeks_calc = GreeksCalculator(model, cr)
            new_delta = greeks_calc.delta()

            pnl = cw_new - cw_price
            pnl_pct = (pnl / cw_price * 100) if cw_price > 0 else 0

            # Lãi/Lỗ vị thế
            qty = cw.get("quantity")
            entry_p = cw.get("entry_price")
            pnl_pos = ""
            if qty and entry_p and qty > 0 and entry_p > 0:
                pnl_vnd = (cw_new - entry_p) * qty
                pnl_pos = f"<div style='font-size:11px;color:#94A3B8;'>Vị thế: {pnl_vnd:+,.0f}đ</div>"

            pnl_color = "#22C55E" if pnl >= 0 else "#EF4444"

            st.markdown(
                f'<div class="scenario-card" style="border-left:3px solid {sc["color"]};">'
                f'<h4 style="color:{sc["color"]};margin:0 0 4px 0;font-size:14px;">'
                f'{sc["name"]}</h4>'
                f'<div style="font-size:11px;color:#8896AB;margin-bottom:8px;">'
                f'{sc["desc"]}</div>'
                f'<div style="font-size:13px;color:#F1F5F9;">'
                f'CW: <b>{format_vnd(cw_new)}</b> đ</div>'
                f'<div style="font-size:15px;font-weight:700;color:{pnl_color};">'
                f'{pnl_pct:+.1f}%</div>'
                f'<div style="font-size:11px;color:#94A3B8;">'
                f'Delta = {new_delta:.4f}</div>'
                f'{pnl_pos}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ============================================================
# 4. ĐƯỜNG SUY GIẢM HOÀ VỐN
# ============================================================

def _render_breakeven_decay(analyzer, cw):
    """Biểu đồ đường: X = Ngày nắm giữ, Y = Giá cơ sở cần để hòa vốn."""
    section_title("📉", "Đường Suy Giảm Hoà Vốn")

    S = cw["S"]
    K = cw["K"]
    cr = cw["cr"]
    cw_price = cw["cw_price"]
    max_days = int(cw["T"] * 365)
    if max_days < 2:
        max_days = 2

    ref_price = cw.get("entry_price") if (cw.get("entry_price") or 0) > 0 else cw_price

    # Tính giá hoà vốn theo từng ngày nắm giữ
    num_points = min(20, max_days)
    hold_days = np.linspace(0, max_days - 1, num_points, dtype=int).tolist()
    hold_days = sorted(set(hold_days))

    be_prices = []
    for hd in hold_days:
        T_remain = max((max_days - hd) / 365.0, 0.001)
        be = _find_breakeven_price(
            K, T_remain, cw["r"], cw["sigma"], cr,
            cw["option_type"], cw.get("q", 0.0), ref_price, S,
        )
        be_prices.append(be)

    col_chart, col_info = st.columns([2, 1])

    with col_chart:
        chart_container("Điểm Hoà Vốn Theo Ngày Nắm Giữ")
        fig = create_breakeven_decay_chart(hold_days, be_prices, S)
        st.plotly_chart(fig, use_container_width=True)
        chart_container_end()

    with col_info:
        # Các mốc quan trọng
        st.markdown(
            '<div style="padding:12px;">'
            '<h4 style="color:#B8C2DB;margin:0 0 12px 0;">📌 Mốc Quan Trọng</h4>',
            unsafe_allow_html=True,
        )

        milestones = [0, 5, 10, 20]
        for md in milestones:
            if md >= max_days:
                continue
            T_remain = max((max_days - md) / 365.0, 0.001)
            be = _find_breakeven_price(
                K, T_remain, cw["r"], cw["sigma"], cr,
                cw["option_type"], cw.get("q", 0.0), ref_price, S,
            )
            move_pct = ((be / S) - 1) * 100 if S > 0 else 0
            move_color = "#EF4444" if abs(move_pct) > 5 else "#F59E0B" if abs(move_pct) > 2 else "#22C55E"

            label = "Hôm nay" if md == 0 else f"Sau {md} ngày"
            st.markdown(
                f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                f'<span style="color:#8896AB;font-size:12px;">{label}</span><br>'
                f'<span style="color:#F1F5F9;font-size:14px;font-weight:600;">'
                f'{format_vnd(be)} đ</span> '
                f'<span style="color:{move_color};font-size:12px;">'
                f'(Cơ sở cần {move_pct:+.1f}%)</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 5. BẢNG PHÂN TÍCH THEO THỜI GIAN NẮM GIỮ
# ============================================================

def _render_holding_analysis(analyzer, cw):
    """Bảng: Cột = thời gian nắm giữ, Hàng = chỉ số quan trọng."""
    section_title("📋", "Phân Tích Theo Thời Gian Nắm Giữ")

    S = cw["S"]
    K = cw["K"]
    cr = cw["cr"]
    sigma = cw["sigma"]
    cw_price = cw["cw_price"]
    max_days = int(cw["T"] * 365)
    ref_price = cw.get("entry_price") if (cw.get("entry_price") or 0) > 0 else cw_price

    periods = [1, 3, 5, 10, 20]
    periods = [p for p in periods if p < max_days]

    if not periods:
        st.warning("CW còn quá ít ngày để phân tích thời gian nắm giữ.")
        return

    rows = []

    # Hàng 1: Giá cơ sở cần để hoà vốn
    be_row = {"Chỉ Số": "Cơ sở cần để hoà vốn"}
    for p in periods:
        T_remain = max((max_days - p) / 365.0, 0.001)
        be = _find_breakeven_price(
            K, T_remain, cw["r"], sigma, cr,
            cw["option_type"], cw.get("q", 0.0), ref_price, S,
        )
        be_row[f"{p} ngày"] = f"{format_vnd(be)} đ"
    rows.append(be_row)

    # Hàng 2: % cơ sở cần thay đổi
    move_row = {"Chỉ Số": "Cơ sở cần thay đổi (%)"}
    for p in periods:
        T_remain = max((max_days - p) / 365.0, 0.001)
        be = _find_breakeven_price(
            K, T_remain, cw["r"], sigma, cr,
            cw["option_type"], cw.get("q", 0.0), ref_price, S,
        )
        move_pct = ((be / S) - 1) * 100 if S > 0 else 0
        move_row[f"{p} ngày"] = f"{move_pct:+.1f}%"
    rows.append(move_row)

    # Hàng 3: Lãi/Lỗ nếu cơ sở tăng 1 độ lệch chuẩn
    sigma_1d = sigma / np.sqrt(252)  # biến động ngày
    pnl_up_row = {"Chỉ Số": "Lãi/Lỗ nếu cơ sở +1σ"}
    for p in periods:
        T_remain = max((max_days - p) / 365.0, 0.001)
        move = sigma_1d * np.sqrt(p)  # quy mô √t
        new_S = S * (1 + move)
        model = BlackScholesModel(
            new_S, K, T_remain, cw["r"], sigma,
            cw["option_type"], q=cw.get("q", 0.0),
        )
        cw_new = model.price() / cr
        pnl_pct = ((cw_new / ref_price) - 1) * 100 if ref_price > 0 else 0
        pnl_up_row[f"{p} ngày"] = f"{pnl_pct:+.1f}%"
    rows.append(pnl_up_row)

    # Hàng 4: Lỗ tối đa nếu giá đi ngang
    flat_row = {"Chỉ Số": "Lỗ tối đa nếu đi ngang"}
    for p in periods:
        T_remain = max((max_days - p) / 365.0, 0.001)
        model = BlackScholesModel(
            S, K, T_remain, cw["r"], sigma,
            cw["option_type"], q=cw.get("q", 0.0),
        )
        cw_flat = model.price() / cr
        loss_pct = ((cw_flat / ref_price) - 1) * 100 if ref_price > 0 else 0
        flat_row[f"{p} ngày"] = f"{loss_pct:+.1f}%"
    rows.append(flat_row)

    # Hàng 5: Đòn bẩy hiệu dụng
    lev_row = {"Chỉ Số": "Đòn bẩy hiệu dụng"}
    for p in periods:
        T_remain = max((max_days - p) / 365.0, 0.001)
        model = BlackScholesModel(
            S, K, T_remain, cw["r"], sigma,
            cw["option_type"], q=cw.get("q", 0.0),
        )
        gc = GreeksCalculator(model, cr)
        raw_delta = abs(gc.delta_raw())
        cw_t = model.price() / cr
        denom = cw_t * cr
        gear = S / denom if denom > 0 else 0
        eff_lev = raw_delta * gear
        lev_row[f"{p} ngày"] = f"{eff_lev:.1f}x"
    rows.append(lev_row)

    # Hàng 6: Xác suất có lãi (gần đúng, trung tính rủi ro)
    pop_row = {"Chỉ Số": "Xác suất có lãi"}
    from scipy.stats import norm as _norm
    for p in periods:
        T_remain = max((max_days - p) / 365.0, 0.001)
        T_hold = max(p / 365.0, 0.001)  # Khoảng thời gian = thời gian nắm giữ
        be = _find_breakeven_price(
            K, T_remain, cw["r"], sigma, cr,
            cw["option_type"], cw.get("q", 0.0), ref_price, S,
        )
        if sigma > 0 and T_hold > 0 and be > 0:
            d2_be = (np.log(S / be) + (cw["r"] - cw.get("q", 0.0) - 0.5 * sigma**2) * T_hold) / (sigma * np.sqrt(T_hold))
            if cw["option_type"] == "call":
                pop = _norm.cdf(d2_be) * 100
            else:
                pop = _norm.cdf(-d2_be) * 100
        else:
            pop = 0
        pop_row[f"{p} ngày"] = f"{pop:.1f}%"
    rows.append(pop_row)

    df = pd.DataFrame(rows)

    table_container("Chỉ Số Theo Thời Gian Nắm Giữ", badge=f"{len(periods)} giai đoạn")
    st.dataframe(df, use_container_width=True, hide_index=True)
    table_container_end()


# ============================================================
# 6. TỰ TẠO KỊCH BẢN
# ============================================================

def _render_custom_scenario(analyzer, cw):
    """Người dùng nhập % thay đổi giá, điểm IV, số ngày nắm giữ → kết quả chi tiết."""
    section_title("🔧", "Tự Tạo Kịch Bản")

    S = cw["S"]
    K = cw["K"]
    cr = cw["cr"]
    sigma = cw["sigma"]
    cw_price = cw["cw_price"]
    max_days = max(int(cw["T"] * 365), 2)

    col1, col2, col3 = st.columns(3)

    with col1:
        ds_pct = st.slider(
            "Thay đổi giá cơ sở (%)",
            min_value=-30.0, max_value=30.0,
            value=0.0, step=0.5,
            key="custom_ds",
        )
    with col2:
        div_pts = st.slider(
            "Thay đổi biến động ngầm định (điểm)",
            min_value=-15.0, max_value=15.0,
            value=0.0, step=0.5,
            key="custom_div",
        )
    with col3:
        hold_max = max(min(max_days - 1, 90), 1)
        hold = st.slider(
            "Số ngày nắm giữ",
            min_value=0, max_value=hold_max,
            value=0, step=1,
            key="custom_hold",
        )

    new_S = S * (1 + ds_pct / 100.0)
    new_sigma = max(sigma + div_pts / 100.0, 0.01)
    T_new = max((max_days - hold) / 365.0, 0.001)

    # Giá trị hiện tại
    model_current = BlackScholesModel(
        S, K, cw["T"], cw["r"], sigma,
        cw["option_type"], q=cw.get("q", 0.0),
    )
    greeks_current = GreeksCalculator(model_current, cr)
    current_greeks = greeks_current.all_greeks()

    # Giá trị kịch bản mới
    model_new = BlackScholesModel(
        new_S, K, T_new, cw["r"], new_sigma,
        cw["option_type"], q=cw.get("q", 0.0),
    )
    cw_new = model_new.price() / cr
    greeks_new = GreeksCalculator(model_new, cr)
    new_greeks = greeks_new.all_greeks()

    pnl = cw_new - cw_price
    pnl_pct = (pnl / cw_price * 100) if cw_price > 0 else 0
    pnl_color = "#22C55E" if pnl >= 0 else "#EF4444"

    # Hiển thị kết quả
    st.markdown(
        f'<div style="text-align:center;padding:12px 0;">'
        f'<span style="font-size:18px;color:#8896AB;">Kịch bản: </span>'
        f'<span style="font-size:18px;color:#F1F5F9;font-weight:700;">'
        f'Cơ sở {ds_pct:+.1f}%, Biến động {div_pts:+.1f} điểm, {hold} ngày</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Thẻ kết quả
    r1, r2, r3, r4 = st.columns(4)

    with r1:
        colored_metric(
            "Giá CW Mới",
            f"{format_vnd(cw_new)} đ",
            color=pnl_color,
            delta=f"từ {format_vnd(cw_price)} đ",
        )
    with r2:
        colored_metric("Lãi/Lỗ (%)", f"{pnl_pct:+.1f}%", color=pnl_color)
    with r3:
        colored_metric("Lãi/Lỗ (đ/CW)", f"{pnl:+,.0f} đ", color=pnl_color)
    with r4:
        qty = cw.get("quantity")
        entry_p = cw.get("entry_price")
        if qty and entry_p and qty > 0 and entry_p > 0:
            pnl_total = (cw_new - entry_p) * qty
            t_color = "#22C55E" if pnl_total >= 0 else "#EF4444"
            colored_metric("Lãi/Lỗ Vị Thế", f"{pnl_total:+,.0f} đ", color=t_color)
        else:
            colored_metric("Giá Cổ Sở Mới", f"{format_vnd(new_S)} đ", color="#3B82F6")

    # Bảng so sánh chỉ số Hy Lạp
    section_divider()

    compare_data = [
        {
            "Chỉ Số": "Delta (Δ)",
            "Hiện Tại": f"{current_greeks['delta']:.4f}",
            "Kịch Bản": f"{new_greeks['delta']:.4f}",
            "Thay Đổi": f"{new_greeks['delta'] - current_greeks['delta']:+.4f}",
        },
        {
            "Chỉ Số": "Gamma (Γ)",
            "Hiện Tại": f"{current_greeks['gamma']:.6f}",
            "Kịch Bản": f"{new_greeks['gamma']:.6f}",
            "Thay Đổi": f"{new_greeks['gamma'] - current_greeks['gamma']:+.6f}",
        },
        {
            "Chỉ Số": "Theta (Θ)",
            "Hiện Tại": f"{current_greeks['theta']:.4f}",
            "Kịch Bản": f"{new_greeks['theta']:.4f}",
            "Thay Đổi": f"{new_greeks['theta'] - current_greeks['theta']:+.4f}",
        },
        {
            "Chỉ Số": "Vega (ν)",
            "Hiện Tại": f"{current_greeks['vega']:.4f}",
            "Kịch Bản": f"{new_greeks['vega']:.4f}",
            "Thay Đổi": f"{new_greeks['vega'] - current_greeks['vega']:+.4f}",
        },
        {
            "Chỉ Số": "Biến động ngầm định",
            "Hiện Tại": format_pct(sigma * 100),
            "Kịch Bản": format_pct(new_sigma * 100),
            "Thay Đổi": f"{div_pts:+.1f} điểm",
        },
    ]

    table_container("Chỉ Số Hy Lạp: Hiện Tại và Kịch Bản", badge="5 chỉ số")
    st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
    table_container_end()
