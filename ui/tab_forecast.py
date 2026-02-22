import streamlit as st
import numpy as np
from core.warrant import WarrantAnalyzer
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import create_scenario_heatmap, create_3d_surface, create_time_decay_chart


def render_forecast_tab(cw):
    """Tab 5: Dự báo giá kỳ vọng và đòn bẩy hiệu dụng."""
    if cw is None:
        tab_empty_state(
            "◇", "Chưa chọn CW để dự báo",
            "Thêm CW vào portfolio ở Sidebar, sau đó chọn CW để xem dự báo giá và phân tích đòn bẩy.",
            "Sidebar → Chọn CW",
        )
        return

    section_title("◇", "Dự Báo Giá Kỳ Vọng & Đòn Bẩy Hiệu Dụng")

    analyzer = WarrantAnalyzer(
        S=cw["S"], K=cw["K"], T=cw["T"],
        r=cw["r"], sigma=cw["sigma"],
        cw_market_price=cw["cw_price"],
        conversion_ratio=cw["cr"],
        option_type=cw["option_type"],
        q=cw.get("q", 0.0),
    )

    # Phần 1: Đòn bẩy
    gearing = analyzer.gearing()
    eff_lev = analyzer.effective_leverage()
    delta = analyzer.greeks.delta()
    delta_raw = abs(analyzer.greeks.delta_raw())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        colored_metric("Đòn Bẩy Đơn Giản", f"{gearing:.2f}x", color="#FF6B35")
    with col2:
        colored_metric("Đòn Bẩy Hiệu Dụng", f"{eff_lev:.2f}x", color="#4ECDC4")
    with col3:
        colored_metric("Delta (adjusted)", f"{delta:.4f}", color="#3B82F6")
    with col4:
        colored_metric("|Delta| (raw)", f"{delta_raw:.4f}", color="#A78BFA")

    option_label = "tăng" if cw["option_type"] == "call" else "giảm"

    st.markdown(
        f'<div class="info-box">'
        f'<b>Đòn bẩy hiệu dụng = {eff_lev:.2f}x</b>: '
        f'Khi giá cơ sở {option_label} <b>1%</b>, giá CW được kỳ vọng '
        f'{option_label} khoảng <b>{eff_lev:.2f}%</b>.<br>'
        f'<small>Công thức: |Delta_raw| × Gearing = '
        f'{delta_raw:.4f} × {gearing:.2f} = {eff_lev:.2f}</small>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Phần 2: Dự báo 3 kịch bản
    section_title("⊕", "Dự Báo 3 Kịch Bản")

    price_changes = [-20, -15, -10, -5, 0, 5, 10, 15, 20]
    vol_changes = [-10, -5, 0, 5, 10]
    scenario_data = analyzer.scenario_prices(price_changes, vol_changes)

    forecast_cols = st.columns(3)
    cw_price = cw["cw_price"]

    with forecast_cols[0]:
        new_S = cw["S"] * 1.10
        cw_up = scenario_data.get((10, 0), 0)
        pnl_up = cw_up - cw_price
        pnl_up_pct = (pnl_up / cw_price) * 100 if cw_price > 0 else 0
        st.markdown(
            f'<div class="scenario-card scenario-card-bullish">'
            f'<h4 style="color:#22C55E;">Kịch Bản Lạc Quan</h4>'
            f'<div class="subtitle" style="color:#86EFAC;">Giá cơ sở +10%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        colored_metric("Giá CS Mới", f"{format_vnd(new_S)} đ", color="#22C55E")
        colored_metric("Giá CW Kỳ Vọng", f"{format_vnd(cw_up)} đ", color="#22C55E", delta=f"{pnl_up_pct:+.1f}%")

    with forecast_cols[1]:
        cw_mid = scenario_data.get((0, 0), 0)
        pnl_mid = cw_mid - cw_price
        pnl_mid_pct = (pnl_mid / cw_price) * 100 if cw_price > 0 else 0
        st.markdown(
            f'<div class="scenario-card scenario-card-neutral">'
            f'<h4 style="color:#3B82F6;">Kịch Bản Trung Tính</h4>'
            f'<div class="subtitle" style="color:#93C5FD;">Giá không đổi</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        colored_metric("Giá CS Hiện Tại", f"{format_vnd(cw['S'])} đ", color="#3B82F6")
        colored_metric("Giá CW Lý Thuyết", f"{format_vnd(cw_mid)} đ", color="#3B82F6", delta=f"{pnl_mid_pct:+.1f}%")

    with forecast_cols[2]:
        new_S_down = cw["S"] * 0.90
        cw_down = scenario_data.get((-10, 0), 0)
        pnl_down = cw_down - cw_price
        pnl_down_pct = (pnl_down / cw_price) * 100 if cw_price > 0 else 0
        st.markdown(
            f'<div class="scenario-card scenario-card-bearish">'
            f'<h4 style="color:#EF4444;">Kịch Bản Bi Quan</h4>'
            f'<div class="subtitle" style="color:#FCA5A5;">Giá cơ sở -10%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        colored_metric("Giá CS Mới", f"{format_vnd(new_S_down)} đ", color="#EF4444")
        colored_metric("Giá CW Kỳ Vọng", f"{format_vnd(cw_down)} đ", color="#EF4444", delta=f"{pnl_down_pct:+.1f}%")

    # Phần 3: Heatmap + Bảng kịch bản
    section_title("▦", "Ma Trận Kịch Bản")

    col_heatmap, col_table = st.columns([1.4, 1])

    with col_heatmap:
        chart_container("Ma trận kịch bản giá CW")
        fig = create_scenario_heatmap(scenario_data, price_changes, vol_changes)
        st.plotly_chart(fig, use_container_width=True)
        chart_container_end()

    with col_table:
        table_container("Giá CW kỳ vọng (Vol không đổi)", badge=f"{len(price_changes)} kịch bản")
        rows = []
        for dp in price_changes:
            new_S = cw["S"] * (1 + dp / 100.0)
            cw_p = scenario_data.get((dp, 0), 0)
            pnl = cw_p - cw_price
            pnl_pct = (pnl / cw_price) * 100 if cw_price > 0 else 0
            rows.append({
                "Giá CS": f"{format_vnd(new_S)}",
                "% Đổi": f"{dp:+d}%",
                "Giá CW": f"{format_vnd(cw_p)}",
                "Lời/Lỗ (đ)": f"{pnl:+,.0f}",
                "% L/L": f"{pnl_pct:+.1f}%",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
        table_container_end()

    # Phần 4: Time Decay + 3D Surface
    section_title("⧖", "Phân Tích Nâng Cao")

    col_decay, col_3d = st.columns(2)

    with col_decay:
        chart_container("Suy giảm giá trị theo thời gian")
        max_days = int(cw["T"] * 365)
        if max_days < 1:
            max_days = 1
        step = max(1, max_days // 50)
        days_list = list(range(max_days, 0, -step))
        days_list.sort()

        time_decay = analyzer.time_decay_prices(days_list)
        fig_decay = create_time_decay_chart(time_decay, cw_price)
        st.plotly_chart(fig_decay, use_container_width=True)
        chart_container_end()

    with col_3d:
        chart_container("Giá CW theo giá cơ sở & volatility")
        fig_3d = create_3d_surface(
            cw["S"], cw["K"], cw["T"],
            cw["r"], cw["cr"], cw["option_type"],
            q=cw.get("q", 0.0),
        )
        st.plotly_chart(fig_3d, use_container_width=True)
        chart_container_end()
