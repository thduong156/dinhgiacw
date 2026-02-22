import streamlit as st
from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from ui.components import (
    section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider,
)
from ui.charts import create_greeks_vs_price, create_greeks_vs_time


def render_greeks_tab(cw):
    """Tab 2: Phân tích Greeks."""
    if cw is None:
        tab_empty_state(
            "▪", "Chưa chọn CW để phân tích Greeks",
            "Thêm CW vào portfolio ở Sidebar, sau đó chọn CW để xem chỉ số Greeks.",
            "Sidebar → Chọn CW",
        )
        return

    section_title("▪", "Chỉ Số Greeks")

    model = BlackScholesModel(
        cw["S"], cw["K"], cw["T"],
        cw["r"], cw["sigma"], cw["option_type"],
    )
    calc = GreeksCalculator(model, cw["cr"])
    greeks = calc.all_greeks()

    # 5 metric cards với màu phân biệt
    cols = st.columns(5)

    delta_color = "#4ECDC4" if greeks["delta"] >= 0 else "#E74C3C"
    theta_color = "#E74C3C" if greeks["theta"] < 0 else "#2ECC71"

    with cols[0]:
        colored_metric("Delta", f"{greeks['delta']:.4f}", color=delta_color)
    with cols[1]:
        colored_metric("Gamma", f"{greeks['gamma']:.6f}", color="#FF6B35")
    with cols[2]:
        colored_metric("Vega", f"{greeks['vega']:.4f}", color="#3B82F6")
    with cols[3]:
        colored_metric("Theta (ngày)", f"{greeks['theta']:.4f}", color=theta_color)
    with cols[4]:
        colored_metric("Rho", f"{greeks['rho']:.4f}", color="#A78BFA")

    section_divider()

    # Giải thích ý nghĩa thực tế
    with st.expander("Ý nghĩa thực tế của các chỉ số", expanded=True):
        delta_val = greeks["delta"]

        if cw["option_type"] == "call":
            delta_text = (
                f"Khi giá cổ phiếu cơ sở **tăng 1,000 đ**, "
                f"giá CW tăng khoảng **{abs(delta_val * 1000):.0f} đ**"
            )
        else:
            delta_text = (
                f"Khi giá cổ phiếu cơ sở **tăng 1,000 đ**, "
                f"giá CW giảm khoảng **{abs(delta_val * 1000):.0f} đ**"
            )

        st.markdown(
            f'<div class="info-box">'
            f'<b>Delta = {delta_val:.4f}</b> &mdash; {delta_text}<br>'
            f'<b>Gamma = {greeks["gamma"]:.6f}</b> &mdash; '
            f'Delta thay đổi {greeks["gamma"] * 1000:.4f} khi giá cơ sở tăng 1,000 đ<br>'
            f'<b>Theta = {greeks["theta"]:.4f}</b> &mdash; '
            f'CW mất <b>{abs(greeks["theta"]):.2f} đ</b> giá trị mỗi ngày do thời gian<br>'
            f'<b>Vega = {greeks["vega"]:.4f}</b> &mdash; '
            f'Khi volatility tăng 1%, giá CW tăng <b>{greeks["vega"]:.2f} đ</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Biểu đồ sensitivity
    section_title("△", "Biểu Đồ Độ Nhạy")

    col1, col2 = st.columns(2)

    with col1:
        chart_container("Delta & Gamma theo giá cơ sở")
        fig_price = create_greeks_vs_price(
            cw["S"], cw["K"], cw["T"],
            cw["r"], cw["sigma"], cw["cr"],
            cw["option_type"], q=cw.get("q", 0.0),
        )
        st.plotly_chart(fig_price, use_container_width=True)
        chart_container_end()

    with col2:
        chart_container("Greeks theo thời gian còn lại")
        fig_time = create_greeks_vs_time(
            cw["S"], cw["K"], cw["T"],
            cw["r"], cw["sigma"], cw["cr"],
            cw["option_type"], q=cw.get("q", 0.0),
        )
        st.plotly_chart(fig_time, use_container_width=True)
        chart_container_end()
