import streamlit as st
import pandas as pd
from core.warrant import WarrantAnalyzer
from ui.components import (
    format_vnd, format_pct, section_title,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import create_batch_pd_bar, create_batch_leverage_scatter


def render_batch_tab():
    """Tab 6: Phân tích hàng loạt TẤT CẢ CW trong portfolio."""
    section_title("📋", "Phân Tích Hàng Loạt CW")

    st.markdown(
        '<div class="info-box">'
        '<b>Phân tích tất cả CW trong portfolio.</b><br>'
        'Thêm CW ở <b>Sidebar → Danh Sách CW Portfolio</b> '
        '(thủ công hoặc upload CSV), sau đó quay lại tab này để xem kết quả.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Đọc portfolio từ session_state
    portfolio = st.session_state.get("cw_portfolio", [])

    if len(portfolio) == 0:
        tab_empty_state(
            "📋",
            "Chưa có CW nào trong Portfolio",
            "Thêm CW ở Sidebar (thủ công hoặc upload CSV), "
            "sau đó quay lại tab này để phân tích hàng loạt.",
            "Sidebar → Thêm CW hoặc Import CSV",
        )
        return

    st.success(f"Đang phân tích **{len(portfolio)}** CW trong portfolio")

    # Phân tích từng CW
    results = []
    progress_bar = st.progress(0, text="Đang phân tích...")

    for idx, cw in enumerate(portfolio):
        progress_bar.progress(
            (idx + 1) / len(portfolio),
            text=f"Đang phân tích {idx + 1}/{len(portfolio)}...",
        )

        try:
            analyzer = WarrantAnalyzer(
                S=cw["S"],
                K=cw["K"],
                T=cw["T"],
                r=cw["r"],
                sigma=cw["sigma"],
                cw_market_price=cw["cw_price"],
                conversion_ratio=cw["cr"],
                option_type=cw["option_type"],
                q=cw.get("q", 0.0),
            )

            analysis = analyzer.full_analysis()

            # Probability of Profit, Theta Efficiency
            prob_profit = analysis.get("probability_of_profit", 0)
            theta_eff = analysis.get("theta_efficiency", 0)
            price_tick = analysis.get("theoretical_price_tick", analysis["theoretical_price"])

            result_row = {
                "Mã CW": cw.get("ma_cw", f"CW #{idx}"),
                "TCPH": cw.get("issuer", "—"),
                "Mã CS": cw.get("ma_co_so", "N/A"),
                "Loại": cw["option_type"].upper(),
                "Giá CS": format_vnd(cw["S"]),
                "Strike": format_vnd(cw["K"]),
                "Giá CW TT": format_vnd(cw["cw_price"]),
                "Giá CW LT": format_vnd(price_tick),
                "Trạng Thái": analysis["premium_discount"]["status"],
                "P/D %": f"{analysis['premium_discount']['percentage']:+.2f}%",
                "XS Lãi": f"{prob_profit*100:.1f}%",
                "Delta": f"{analysis['greeks']['delta']:.4f}",
                "Đòn Bẩy": f"{analysis['effective_leverage']:.2f}x",
                "Theta Eff": f"{theta_eff:.0f}d" if theta_eff < 999 else "∞",
                "Moneyness": analysis["moneyness"],
            }

            # Tính IV
            if analysis["implied_volatility"] is not None:
                result_row["IV"] = format_pct(analysis["implied_volatility"] * 100)
            else:
                result_row["IV"] = "N/A"

            # Position P&L nếu có
            entry_p = cw.get("entry_price")
            qty = cw.get("quantity")
            if entry_p and qty and entry_p > 0 and qty > 0:
                pnl = (cw["cw_price"] - entry_p) * qty
                pnl_pct = ((cw["cw_price"] / entry_p) - 1) * 100
                result_row["SL"] = f"{qty:,}"
                result_row["P&L"] = f"{pnl:+,.0f}đ ({pnl_pct:+.1f}%)"

            # Lưu raw values cho charts
            result_row["_pd_pct"] = analysis["premium_discount"]["percentage"]
            result_row["_leverage"] = analysis["effective_leverage"]

            results.append(result_row)

        except Exception as e:
            results.append({
                "Mã CW": cw.get("ma_cw", f"CW #{idx}"),
                "Mã CS": cw.get("ma_co_so", "N/A"),
                "Loại": cw.get("option_type", "?"),
                "Lỗi": str(e),
            })

    progress_bar.empty()

    # Kết quả
    section_title("📊", "Kết Quả Phân Tích")

    # DataFrame hiển thị (bỏ cột _raw)
    display_results = []
    for r in results:
        display_row = {k: v for k, v in r.items() if not k.startswith("_")}
        display_results.append(display_row)

    result_df = pd.DataFrame(display_results)
    table_container("Kết Quả Phân Tích", badge=f"{len(results)} CW")
    st.dataframe(result_df, use_container_width=True, hide_index=True)
    table_container_end()

    # Thống kê tổng hợp
    valid_results = [r for r in results if "Lỗi" not in r]
    if valid_results:
        section_divider()
        section_title("📈", "Thống Kê Tổng Hợp")

        premium_count = sum(1 for r in valid_results if r["Trạng Thái"] == "Premium")
        discount_count = sum(1 for r in valid_results if r["Trạng Thái"] == "Discount")
        fair_count = sum(1 for r in valid_results if r["Trạng Thái"] == "Fair")

        # Batch stats grid
        st.markdown(
            f'<div class="batch-stats-grid">'
            f'<div class="batch-stat-card total">'
            f'<div class="batch-stat-card-value" style="color:#FF6B35;">'
            f'{len(valid_results)}</div>'
            f'<div class="batch-stat-card-label">Tổng CW Phân Tích</div></div>'
            f'<div class="batch-stat-card bsc-discount">'
            f'<div class="batch-stat-card-value" style="color:#22C55E;">'
            f'{discount_count}</div>'
            f'<div class="batch-stat-card-label">Discount (Rẻ)</div></div>'
            f'<div class="batch-stat-card bsc-premium">'
            f'<div class="batch-stat-card-value" style="color:#EF4444;">'
            f'{premium_count}</div>'
            f'<div class="batch-stat-card-label">Premium (Đắt)</div></div>'
            f'<div class="batch-stat-card bsc-fair">'
            f'<div class="batch-stat-card-value" style="color:#3B82F6;">'
            f'{fair_count}</div>'
            f'<div class="batch-stat-card-label">Fair Value</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Charts tổng quan
        names = [r["Mã CW"] for r in valid_results]
        pd_pcts = [r["_pd_pct"] for r in valid_results]
        leverages = [r["_leverage"] for r in valid_results]

        section_divider()

        col_bar, col_scatter = st.columns(2)

        with col_bar:
            chart_container("Premium / Discount từng CW")
            fig_pd = create_batch_pd_bar(names, pd_pcts)
            st.plotly_chart(fig_pd, use_container_width=True)
            chart_container_end()

        with col_scatter:
            chart_container("Đòn Bẩy vs Định Giá")
            fig_scatter = create_batch_leverage_scatter(names, pd_pcts, leverages)
            st.plotly_chart(fig_scatter, use_container_width=True)
            chart_container_end()

    # Xuất CSV
    section_divider()
    csv_data = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Tải Kết Quả (CSV)",
        data=csv_data,
        file_name="phan_tich_chung_quyen.csv",
        mime="text/csv",
    )
