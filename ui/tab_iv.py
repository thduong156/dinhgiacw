import streamlit as st
from core.implied_volatility import solve_implied_volatility
from core.black_scholes import BlackScholesModel
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import create_iv_sensitivity


def render_iv_tab(cw):
    """Tab 3: Biến động ngầm định (Implied Volatility)."""
    if cw is None:
        tab_empty_state(
            "📉", "Chưa chọn CW để phân tích IV",
            "Thêm CW vào portfolio ở Sidebar, sau đó chọn CW để xem phân tích Implied Volatility.",
            "Sidebar → Chọn CW",
        )
        return

    section_title("📉", "Biến Động Ngầm Định (Implied Volatility)")

    # IV Solver
    iv = None
    iv_error = None
    try:
        iv = solve_implied_volatility(
            market_price=cw["cw_price"],
            S=cw["S"],
            K=cw["K"],
            T=cw["T"],
            r=cw["r"],
            conversion_ratio=cw["cr"],
            option_type=cw["option_type"],
            q=cw.get("q", 0.0),
        )
    except (ValueError, RuntimeError) as e:
        iv_error = str(e)

    # Row metric chính
    c1, c2, c3 = st.columns(3)

    with c1:
        if iv is not None:
            colored_metric("Implied Volatility (IV)", format_pct(iv * 100), color="#FF6B35")
        else:
            colored_metric("Implied Volatility (IV)", "N/A", color="#EF4444")

    with c2:
        colored_metric("Input Volatility (σ)", format_pct(cw["sigma"] * 100), color="#4ECDC4")

    with c3:
        if iv is not None:
            diff = iv - cw["sigma"]
            diff_color = "#F59E0B" if diff > 0.01 else "#22C55E" if diff < -0.01 else "#3B82F6"
            colored_metric("Chênh Lệch IV - σ", format_pct(diff * 100), color=diff_color)
        else:
            colored_metric("Chênh Lệch IV - σ", "N/A", color="#718096")

    section_divider()

    # Nhận định
    if iv is not None:
        diff = iv - cw["sigma"]
        if diff > 0.01:
            st.markdown(
                f'<div class="warning-box">'
                f'IV <b>cao hơn</b> biến động đầu vào '
                f'<b>{format_pct(abs(diff * 100))}</b>. '
                f'Thị trường đang kỳ vọng biến động <b>mạnh hơn</b> so với ước tính của bạn. '
                f'CW có thể đang được định giá cao.'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif diff < -0.01:
            st.markdown(
                f'<div class="success-box">'
                f'IV <b>thấp hơn</b> biến động đầu vào '
                f'<b>{format_pct(abs(diff * 100))}</b>. '
                f'Thị trường đang kỳ vọng biến động <b>yếu hơn</b> so với ước tính của bạn. '
                f'CW có thể đang được định giá thấp.'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="info-box">'
                f'IV <b>gần bằng</b> với biến động đầu vào. '
                f'Thị trường và ước tính của bạn đang đồng thuận.'
                f'</div>',
                unsafe_allow_html=True,
            )
    elif iv_error:
        st.error(f"Không thể tính IV: {iv_error}")

    # Biểu đồ + Bảng sensitivity
    section_divider()

    col_chart, col_table = st.columns([1.3, 1])

    with col_chart:
        section_title("📈", "Độ Nhạy Giá CW theo Volatility")
        chart_container("Giá CW lý thuyết theo volatility")
        fig = create_iv_sensitivity(
            cw["S"], cw["K"], cw["T"],
            cw["r"], cw["cr"], cw["option_type"],
            cw["sigma"], q=cw.get("q", 0.0),
        )
        st.plotly_chart(fig, use_container_width=True)
        chart_container_end()

    with col_table:
        section_title("📋", "Bảng Giá CW theo Mức Volatility")
        vol_levels = [-15, -10, -5, 0, 5, 10, 15]
        rows = []
        for dv in vol_levels:
            new_sigma = cw["sigma"] + dv / 100.0
            if new_sigma <= 0:
                continue
            model = BlackScholesModel(
                cw["S"], cw["K"], cw["T"],
                cw["r"], new_sigma, cw["option_type"],
                q=cw.get("q", 0.0),
            )
            cw_p = model.price() / cw["cr"]
            change = cw_p - cw["cw_price"]
            rows.append({
                "Volatility": format_pct(new_sigma * 100),
                "Thay Đổi": f"{dv:+d}%",
                "Giá CW (đ)": format_vnd(cw_p),
                "Chênh Lệch (đ)": f"{change:+,.0f}",
            })

        table_container("Giá CW theo Volatility", badge=f"{len(rows)} mức")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        table_container_end()

    # Giải thích
    with st.expander("Implied Volatility là gì?", expanded=False):
        st.markdown(
            "- **Implied Volatility (IV)** là mức biến động mà thị trường "
            "đang 'định giá' vào chứng quyền.\n"
            "- Nếu **IV > σ nhập vào**: CW có thể đang định giá cao.\n"
            "- Nếu **IV < σ nhập vào**: CW có thể đang định giá thấp.\n"
            "- IV được tính bằng phương pháp **Newton-Raphson** "
            "với bisection fallback để đảm bảo hội tụ."
        )
