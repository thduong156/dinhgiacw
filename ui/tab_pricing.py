import streamlit as st
from core.warrant import WarrantAnalyzer
from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from core.implied_volatility import solve_implied_volatility
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import create_payoff_diagram


def _quick_summary(analyzer, cw):
    """Tổng quan nhanh: Dashboard tín hiệu + điểm chính."""
    analysis = analyzer.full_analysis()
    pd_info = analysis["premium_discount"]
    greeks = analysis["greeks"]

    # --- Tính điểm tổng hợp (score 0-100) ---
    score = 50  # Bắt đầu trung tính
    signals = []

    # 1) Premium / Discount
    pd_pct = pd_info["percentage"]
    if pd_pct < -10:
        score += 20
        signals.append(("🟢", "Discount lớn", f"{pd_pct:+.1f}%"))
    elif pd_pct < -3:
        score += 10
        signals.append(("🟢", "Discount nhẹ", f"{pd_pct:+.1f}%"))
    elif pd_pct > 15:
        score -= 20
        signals.append(("🔴", "Premium quá cao", f"{pd_pct:+.1f}%"))
    elif pd_pct > 5:
        score -= 10
        signals.append(("🟡", "Premium vừa phải", f"{pd_pct:+.1f}%"))
    else:
        signals.append(("🟢", "Giá hợp lý", f"{pd_pct:+.1f}%"))

    # 2) Moneyness
    moneyness = analysis["moneyness"]
    if "ITM" in moneyness:
        score += 10
        signals.append(("🟢", "Trong tiền (ITM)", "Có giá trị nội tại"))
    elif "OTM" in moneyness:
        score -= 10
        signals.append(("🟡", "Ngoài tiền (OTM)", "Chỉ có giá trị thời gian"))
    else:
        signals.append(("🟢", "Ngang giá (ATM)", "Delta nhạy nhất"))

    # 3) Thời gian còn lại
    days = cw["days_remaining"]
    if days < 30:
        score -= 20
        signals.append(("🔴", "Sắp đáo hạn", f"Còn {days} ngày"))
    elif days < 60:
        score -= 10
        signals.append(("🟡", "Thời gian ngắn", f"Còn {days} ngày"))
    elif days > 180:
        score += 5
        signals.append(("🟢", "Thời gian thoải mái", f"Còn {days} ngày"))
    else:
        signals.append(("🟢", "Thời gian hợp lý", f"Còn {days} ngày"))

    # 4) Đòn bẩy hiệu dụng
    eff_lev = analysis["effective_leverage"]
    if eff_lev > 10:
        signals.append(("🟡", "Đòn bẩy rất cao", f"{eff_lev:.1f}x"))
        score -= 5
    elif eff_lev > 5:
        signals.append(("🟢", "Đòn bẩy tốt", f"{eff_lev:.1f}x"))
        score += 5
    elif eff_lev > 2:
        signals.append(("🟢", "Đòn bẩy vừa phải", f"{eff_lev:.1f}x"))
    else:
        signals.append(("🟡", "Đòn bẩy thấp", f"{eff_lev:.1f}x"))

    # 5) Break-even
    be_pct = abs(analysis["break_even_change_pct"])
    if be_pct > 20:
        score -= 10
        signals.append(("🔴", "Hoà vốn xa", f"Cần {be_pct:.1f}%"))
    elif be_pct > 10:
        score -= 5
        signals.append(("🟡", "Hoà vốn khá xa", f"Cần {be_pct:.1f}%"))
    else:
        score += 5
        signals.append(("🟢", "Hoà vốn gần", f"Cần {be_pct:.1f}%"))

    # 6) Probability of Profit
    prob_profit = analysis.get("probability_of_profit", 0)
    if prob_profit > 0.5:
        score += 5
        signals.append(("🟢", "Xác suất lãi cao", f"{prob_profit*100:.0f}%"))
    elif prob_profit > 0.3:
        signals.append(("🟡", "Xác suất lãi TB", f"{prob_profit*100:.0f}%"))
    else:
        score -= 5
        signals.append(("🔴", "Xác suất lãi thấp", f"{prob_profit*100:.0f}%"))

    # 7) Theta Efficiency
    theta_eff_val = analysis.get("theta_efficiency", 0)
    if theta_eff_val >= 999:
        score += 5
        signals.append(("🟢", "Theta rất tốt", "∞ (theta ≈ 0)"))
    elif theta_eff_val > 80:
        signals.append(("🟢", "Theta tốt", f"{theta_eff_val:.0f} ngày"))
    elif theta_eff_val > 40:
        signals.append(("🟡", "Theta TB", f"{theta_eff_val:.0f} ngày"))
    else:
        score -= 5
        signals.append(("🔴", "Theta xấu", f"{theta_eff_val:.0f} ngày"))

    # Clamp score
    score = max(0, min(100, score))

    # Xác định tín hiệu tổng
    if score >= 70:
        signal_text = "TÍCH CỰC"
        signal_color = "#22C55E"
        signal_desc = "Các chỉ số cho thấy CW có điều kiện thuận lợi."
    elif score >= 40:
        signal_text = "TRUNG TÍNH"
        signal_color = "#F59E0B"
        signal_desc = "CW ở mức trung bình, cần cân nhắc kỹ."
    else:
        signal_text = "THẬN TRỌNG"
        signal_color = "#EF4444"
        signal_desc = "Nhiều chỉ số bất lợi, cần xem xét cẩn thận."

    # --- RENDER ---
    col_signal, col_metrics = st.columns([1, 2.5])

    with col_signal:
        st.markdown(
            f'<div class="quick-summary-signal">'
            f'<div class="signal-score" style="color:{signal_color};">{score}</div>'
            f'<div class="signal-label" style="color:{signal_color};">'
            f'{signal_text}</div>'
            f'<div class="signal-desc">{signal_desc}</div>'
            f'<div class="signal-bar">'
            f'<div class="signal-bar-fill" style="width:{score}%; '
            f'background:linear-gradient(90deg, #EF4444, #F59E0B, #22C55E);"></div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_metrics:
        # Row 1: 3 metric cards
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            colored_metric(
                "Giá LT / TT",
                f"{format_vnd(analysis['theoretical_price'])} / {format_vnd(cw['cw_price'])}",
                color=signal_color,
            )
        with mc2:
            colored_metric("Đòn Bẩy Hiệu Dụng", f"{eff_lev:.2f}x", color="#4ECDC4")
        with mc3:
            iv = analysis.get("implied_volatility")
            iv_text = f"{iv*100:.1f}%" if iv else "N/A"
            colored_metric("IV (Ngầm Định)", iv_text, color="#A78BFA")

        # Row 2: Probability + Theta
        mc4, mc5, mc6 = st.columns(3)
        with mc4:
            pp = analysis.get("probability_of_profit", 0)
            pp_c = "#22C55E" if pp > 0.5 else "#F59E0B" if pp > 0.3 else "#EF4444"
            colored_metric("Xác Suất Lãi", f"{pp*100:.1f}%", color=pp_c)
        with mc5:
            te = analysis.get("theta_efficiency", 0)
            te_c = "#22C55E" if te > 80 else "#F59E0B" if te > 40 else "#EF4444"
            te_txt = f"{te:.0f} ngày" if te < 999 else "∞"
            colored_metric("Theta Efficiency", te_txt, color=te_c)
        with mc6:
            issuer_val = cw.get("issuer", "—")
            colored_metric("TCPH", issuer_val if issuer_val else "—", color="#93C5FD")

        # Signal tags
        st.markdown(
            '<div class="quick-summary-signals">'
            + "".join(
                f'<div class="signal-item">'
                f'<span class="signal-item-icon">{icon}</span>'
                f'<span class="signal-item-label">{label}</span>'
                f'<span class="signal-item-detail">{detail}</span>'
                f'</div>'
                for icon, label, detail in signals
            )
            + '</div>',
            unsafe_allow_html=True,
        )

    # Disclaimer
    st.markdown(
        '<div style="text-align:center; font-size:0.68rem; color:#475569; '
        'margin-top:4px; margin-bottom:8px; font-style:italic;">'
        'Điểm số mang tính tham khảo từ mô hình. '
        'Không phải khuyến nghị đầu tư.'
        '</div>',
        unsafe_allow_html=True,
    )


def render_pricing_tab(cw):
    """Tab 1: Định giá chứng quyền."""
    if cw is None:
        tab_empty_state(
            "◈", "Chưa chọn CW để phân tích",
            "Thêm CW vào portfolio ở Sidebar, sau đó chọn CW để xem định giá chi tiết.",
            "Sidebar → Thêm CW",
        )
        return

    analyzer = WarrantAnalyzer(
        S=cw["S"], K=cw["K"], T=cw["T"],
        r=cw["r"], sigma=cw["sigma"],
        cw_market_price=cw["cw_price"],
        conversion_ratio=cw["cr"],
        option_type=cw["option_type"],
        q=cw.get("q", 0.0),
    )

    # ===== TỔNG QUAN NHANH =====
    section_title("▸", "Tổng Quan Nhanh")
    _quick_summary(analyzer, cw)

    # ===== ĐỊNH GIÁ CHI TIẾT =====
    section_title("◆", "Định Giá Chứng Quyền (Black-Scholes)")

    # Kết quả chính
    theo_price = analyzer.theoretical_cw_price()
    intrinsic = analyzer.intrinsic_value()
    time_val = analyzer.time_value()
    moneyness = analyzer.moneyness()
    be = analyzer.break_even()
    be_pct = analyzer.break_even_change_pct()

    # Row 1: 4 metric cards chính
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        colored_metric("Giá CW Lý Thuyết", f"{format_vnd(theo_price)} đ", color="#FF6B35")
    with c2:
        colored_metric("Giá CW Thị Trường", f"{format_vnd(cw['cw_price'])} đ", color="#F1F5F9")
    with c3:
        colored_metric("Giá Trị Nội Tại", f"{format_vnd(intrinsic)} đ", color="#22C55E")
    with c4:
        colored_metric("Giá Trị Thời Gian", f"{format_vnd(time_val)} đ", color="#A78BFA")

    # Row 2: Trạng thái + Hoà vốn
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        mn_color = "#22C55E" if "ITM" in moneyness else "#EF4444" if "OTM" in moneyness else "#F59E0B"
        colored_metric("Trạng Thái (Moneyness)", moneyness, color=mn_color)
    with c6:
        colored_metric("Điểm Hoà Vốn", f"{format_vnd(be)} đ", color="#4ECDC4")
    with c7:
        colored_metric("Cần Đổi Để Hoà Vốn", format_pct(be_pct), color="#F59E0B")
    with c8:
        days = cw['days_remaining']
        days_color = "#EF4444" if days < 30 else "#F59E0B" if days < 90 else "#22C55E"
        colored_metric("Số Ngày Còn Lại", f"{days} ngày", color=days_color)

    # Row 3: Chỉ số nâng cao — Probability, Theta Eff, Price Tick, Issuer
    full = analyzer.full_analysis()
    prob_profit = full.get("probability_of_profit", 0)
    prob_itm = full.get("probability_itm", 0)
    theta_eff = full.get("theta_efficiency", 0)
    price_tick = full.get("theoretical_price_tick", theo_price)

    c9, c10, c11, c12 = st.columns(4)
    with c9:
        pp_color = "#22C55E" if prob_profit > 0.5 else "#F59E0B" if prob_profit > 0.3 else "#EF4444"
        colored_metric("Xác Suất Lãi (P.o.P)", f"{prob_profit*100:.1f}%", color=pp_color)
    with c10:
        pi_color = "#22C55E" if prob_itm > 0.5 else "#F59E0B" if prob_itm > 0.3 else "#EF4444"
        colored_metric("Xác Suất ITM", f"{prob_itm*100:.1f}%", color=pi_color)
    with c11:
        te_color = "#22C55E" if theta_eff > 80 else "#F59E0B" if theta_eff > 40 else "#EF4444"
        te_display = f"{theta_eff:.0f} ngày" if theta_eff < 999 else "∞"
        colored_metric("Theta Efficiency", te_display, color=te_color)
    with c12:
        issuer = cw.get("issuer", "—")
        colored_metric("TCPH / Giá LT (tròn)", f"{issuer} | {format_vnd(price_tick)} đ", color="#93C5FD")

    # Position P&L (nếu có vị thế)
    entry_p = cw.get("entry_price")
    qty = cw.get("quantity")
    if entry_p and qty and entry_p > 0 and qty > 0:
        pnl_vnd = (cw["cw_price"] - entry_p) * qty
        pnl_pct = ((cw["cw_price"] / entry_p) - 1) * 100 if entry_p > 0 else 0
        cost_total = entry_p * qty
        market_val = cw["cw_price"] * qty

        if pnl_vnd >= 0:
            pnl_box = "success-box"
            pnl_label = "LỜI"
            pnl_icon = "△"
        else:
            pnl_box = "danger-box"
            pnl_label = "LỖ"
            pnl_icon = "▽"

        st.markdown(
            f'<div class="{pnl_box}">'
            f'<b>{pnl_icon} VỊ THẾ ĐANG GIỮ:</b> '
            f'{qty:,} CW × {format_vnd(entry_p)} đ = '
            f'{format_vnd(cost_total)} đ &rarr; '
            f'Giá trị hiện tại: <b>{format_vnd(market_val)} đ</b> | '
            f'{pnl_label}: <b>{format_vnd(abs(pnl_vnd))} đ ({pnl_pct:+.1f}%)</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Chênh lệch giá - nổi bật
    diff = cw["cw_price"] - theo_price
    diff_pct = (diff / theo_price * 100) if theo_price > 0 else 0

    if diff > 0.01:
        st.markdown(
            f'<div class="warning-box">'
            f'<b>PREMIUM (Định giá cao)</b> &mdash; '
            f'CW đang giao dịch <b>cao hơn</b> giá lý thuyết '
            f'<b>{format_vnd(abs(diff))} đ ({format_pct(abs(diff_pct))})</b>. '
            f'Nhà đầu tư đang trả thêm phần bù rủi ro.'
            f'</div>',
            unsafe_allow_html=True,
        )
    elif diff < -0.01:
        st.markdown(
            f'<div class="success-box">'
            f'<b>DISCOUNT (Định giá thấp)</b> &mdash; '
            f'CW đang giao dịch <b>thấp hơn</b> giá lý thuyết '
            f'<b>{format_vnd(abs(diff))} đ ({format_pct(abs(diff_pct))})</b>. '
            f'Có thể là cơ hội mua vào.'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="info-box">'
            f'<b>FAIR VALUE</b> &mdash; CW đang giao dịch tại giá trị hợp lý theo mô hình.'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Biểu đồ Payoff
    section_title("▪", "Biểu Đồ Lợi Nhuận (Payoff Diagram)")

    chart_container("Payoff tại đáo hạn vs giá trị hiện tại")
    fig = create_payoff_diagram(
        cw["S"], cw["K"], cw["cw_price"],
        cw["cr"], cw["option_type"],
        cw["sigma"], cw["T"], cw["r"],
    )
    st.plotly_chart(fig, use_container_width=True)
    chart_container_end()

    # ===== SO SÁNH GIÁ LÝ THUYẾT vs THỊ TRƯỜNG =====
    section_divider()
    section_title("⇌", "So Sánh Giá Lý Thuyết vs Thị Trường")

    pd_info = analyzer.premium_discount()

    # Side-by-side panels
    col_theo, col_market = st.columns(2)

    with col_theo:
        section_title("∠", "Lý Thuyết (Black-Scholes)")
        colored_metric("Giá CW Lý Thuyết", f"{format_vnd(pd_info['theoretical_price'])} đ", color="#FF6B35")
        colored_metric("Giá Trị Nội Tại", f"{format_vnd(intrinsic)} đ", color="#22C55E")
        colored_metric("Giá Trị Thời Gian", f"{format_vnd(time_val)} đ", color="#A78BFA")

        with st.expander("Greeks (Input Volatility)"):
            greeks_input = analyzer.greeks.all_greeks()
            for name, val in greeks_input.items():
                st.markdown(f"**{name.capitalize()}**: `{val:.6f}`")

    iv = None
    with col_market:
        section_title("▪", "Thị Trường (Thực Tế)")
        colored_metric("Giá CW Thị Trường", f"{format_vnd(pd_info['market_price'])} đ", color="#F1F5F9")

        try:
            iv = solve_implied_volatility(
                cw["cw_price"], cw["S"], cw["K"],
                cw["T"], cw["r"], cw["cr"],
                cw["option_type"],
            )
            colored_metric("Implied Volatility", format_pct(iv * 100), color="#4ECDC4")

            with st.expander("Greeks (Implied Volatility)"):
                model_iv = BlackScholesModel(
                    cw["S"], cw["K"], cw["T"],
                    cw["r"], iv, cw["option_type"],
                )
                calc_iv = GreeksCalculator(model_iv, cw["cr"])
                greeks_iv = calc_iv.all_greeks()
                for name, val in greeks_iv.items():
                    st.markdown(f"**{name.capitalize()}**: `{val:.6f}`")

        except (ValueError, Exception):
            st.warning("Không thể tính Implied Volatility cho giá thị trường này")

    # Bảng so sánh chi tiết
    section_divider()
    section_title("≡", "Bảng So Sánh Chi Tiết")

    iv_market_str = format_pct(iv * 100) if iv is not None else "N/A"
    iv_diff_str = format_pct((iv - cw["sigma"]) * 100) if iv is not None else "N/A"

    comparison_data = [
        {
            "Chỉ Tiêu": "Giá CW",
            "Lý Thuyết": f"{format_vnd(pd_info['theoretical_price'])} đ",
            "Thị Trường": f"{format_vnd(pd_info['market_price'])} đ",
            "Chênh Lệch": f"{pd_info['difference']:+,.0f} đ ({pd_info['percentage']:+.2f}%)",
        },
        {
            "Chỉ Tiêu": "Giá Trị Nội Tại",
            "Lý Thuyết": f"{format_vnd(intrinsic)} đ",
            "Thị Trường": "-",
            "Chênh Lệch": "-",
        },
        {
            "Chỉ Tiêu": "Giá Trị Thời Gian",
            "Lý Thuyết": f"{format_vnd(time_val)} đ",
            "Thị Trường": "-",
            "Chênh Lệch": "-",
        },
        {
            "Chỉ Tiêu": "Volatility",
            "Lý Thuyết": format_pct(cw["sigma"] * 100),
            "Thị Trường": iv_market_str,
            "Chênh Lệch": iv_diff_str,
        },
        {
            "Chỉ Tiêu": "Điểm Hoà Vốn",
            "Lý Thuyết": f"{format_vnd(be)} đ",
            "Thị Trường": "-",
            "Chênh Lệch": f"{format_pct(be_pct)} từ giá hiện tại",
        },
    ]

    table_container("So Sánh Chi Tiết", badge="5 chỉ tiêu")
    st.dataframe(comparison_data, use_container_width=True, hide_index=True)
    table_container_end()

    # Bảng tham số tổng hợp
    section_divider()
    with st.expander("Xem tham số đang sử dụng", expanded=False):
        param_cols = st.columns(6)
        with param_cols[0]:
            colored_metric("Giá Cơ Sở (S)", f"{format_vnd(cw['S'])} đ", color="#93C5FD")
        with param_cols[1]:
            colored_metric("Strike (K)", f"{format_vnd(cw['K'])} đ", color="#93C5FD")
        with param_cols[2]:
            colored_metric("Thời Gian (T)", f"{cw['T']:.4f} năm", color="#93C5FD")
        with param_cols[3]:
            colored_metric("Lãi Suất (r)", format_pct(cw['r'] * 100), color="#93C5FD")
        with param_cols[4]:
            colored_metric("Volatility (σ)", format_pct(cw['sigma'] * 100), color="#93C5FD")
        with param_cols[5]:
            colored_metric("Tỷ Lệ CĐ (CR)", f"{cw['cr']:.2f}", color="#93C5FD")
