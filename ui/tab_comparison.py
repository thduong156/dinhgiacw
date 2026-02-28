import streamlit as st
from core.warrant import WarrantAnalyzer
from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from core.implied_volatility import solve_implied_volatility
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, section_divider, table_container, table_container_end, render_table,
)


def render_comparison_tab(cw):
    """Tab 4: So sánh giá lý thuyết vs thị trường."""
    if cw is None:
        tab_empty_state(
            "⇌", "Chưa chọn CW để so sánh giá",
            "Thêm CW vào portfolio ở Sidebar, sau đó chọn CW để xem so sánh giá lý thuyết vs thị trường.",
            "Sidebar → Chọn CW",
        )
        return

    section_title("⇌", "So Sánh Giá Lý Thuyết vs Thị Trường")

    analyzer = WarrantAnalyzer(
        S=cw["S"], K=cw["K"], T=cw["T"],
        r=cw["r"], sigma=cw["sigma"],
        cw_market_price=cw["cw_price"],
        conversion_ratio=cw["cr"],
        option_type=cw["option_type"],
        q=cw.get("q", 0.0),
    )

    pd_info = analyzer.premium_discount()

    # Verdict box nổi bật
    if pd_info["status"] == "Premium":
        color = "#E74C3C"
        box_class = "danger-box"
        verdict = (
            f"CW đang <b>ĐỊNH GIÁ CAO</b> hơn giá lý thuyết "
            f"<b>{format_pct(abs(pd_info['percentage']))}</b>. "
            f"Nhà đầu tư đang trả thêm <b>{format_vnd(abs(pd_info['difference']))} đ</b> "
            f"so với giá trị hợp lý."
        )
    elif pd_info["status"] == "Discount":
        color = "#2ECC71"
        box_class = "success-box"
        verdict = (
            f"CW đang <b>ĐỊNH GIÁ THẤP</b> hơn giá lý thuyết "
            f"<b>{format_pct(abs(pd_info['percentage']))}</b>. "
            f"Có thể là cơ hội mua vào nếu tin vào cổ phiếu cơ sở."
        )
    else:
        color = "#3498DB"
        box_class = "info-box"
        verdict = "CW đang giao dịch tại giá trị hợp lý theo mô hình Black-Scholes."

    st.markdown(
        f'<div class="{box_class}"><b>{pd_info["status_vi"]}</b> &mdash; {verdict}</div>',
        unsafe_allow_html=True,
    )

    section_divider()

    # 3 metric so sánh chính
    diff = pd_info["difference"]
    pct = pd_info["percentage"]

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        colored_metric("Chênh Lệch Tuyệt Đối", f"{diff:+,.0f} đ", color=color)
    with mc2:
        colored_metric("Chênh Lệch Tương Đối", f"{pct:+.2f}%", color=color)
    with mc3:
        colored_metric("Trạng Thái", pd_info["status_vi"], color=color)

    section_divider()

    # Side-by-side panels
    col_theo, col_market = st.columns(2)

    with col_theo:
        section_title("∠", "Lý Thuyết (Black-Scholes)")
        colored_metric("Giá CW Lý Thuyết", f"{format_vnd(pd_info['theoretical_price'])} đ", color="#FF6B35")
        colored_metric("Giá Trị Nội Tại", f"{format_vnd(analyzer.intrinsic_value())} đ", color="#22C55E")
        colored_metric("Giá Trị Thời Gian", f"{format_vnd(analyzer.time_value())} đ", color="#A78BFA")

        with st.expander("Greeks (Input Volatility)"):
            greeks = analyzer.greeks.all_greeks()
            for name, val in greeks.items():
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
            "Chênh Lệch": f"{diff:+,.0f} đ ({pct:+.2f}%)",
        },
        {
            "Chỉ Tiêu": "Giá Trị Nội Tại",
            "Lý Thuyết": f"{format_vnd(analyzer.intrinsic_value())} đ",
            "Thị Trường": "-",
            "Chênh Lệch": "-",
        },
        {
            "Chỉ Tiêu": "Giá Trị Thời Gian",
            "Lý Thuyết": f"{format_vnd(analyzer.time_value())} đ",
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
            "Lý Thuyết": f"{format_vnd(analyzer.break_even())} đ",
            "Thị Trường": "-",
            "Chênh Lệch": f"{format_pct(analyzer.break_even_change_pct())} từ giá hiện tại",
        },
    ]

    table_container("So Sánh Chi Tiết", badge="5 chỉ tiêu")
    render_table(comparison_data)
    table_container_end()
