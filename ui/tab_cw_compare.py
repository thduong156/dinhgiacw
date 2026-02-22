import streamlit as st
import pandas as pd
from datetime import date
from core.warrant import WarrantAnalyzer
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import (
    create_radar_chart,
    create_comparison_bar_chart,
    create_overlaid_payoff,
    CW_COLORS,
)


def _get_cw_color(index):
    """Trả về màu cho CW thứ i."""
    return CW_COLORS[index % len(CW_COLORS)]


def _normalize_metrics(analyses):
    """Chuẩn hóa metrics sang thang 0-100 cho radar chart."""
    metric_defs = {
        "|Delta|": lambda a: abs(a["greeks"]["delta"]),
        "Gamma": lambda a: a["greeks"]["gamma"],
        "Vega": lambda a: abs(a["greeks"]["vega"]),
        "Đòn Bẩy": lambda a: a["effective_leverage"],
        "Giá Trị Hợp Lý": lambda a: max(0, 100 - abs(a["premium_discount"]["percentage"])),
        "Thời Gian": lambda a: a["_input"]["days_remaining"],
    }

    result = {a["_name"]: {} for a in analyses}

    for metric_name, extractor in metric_defs.items():
        values = [extractor(a) for a in analyses]
        min_v = min(values)
        max_v = max(values)
        range_v = max_v - min_v if max_v != min_v else 1.0

        for idx, a in enumerate(analyses):
            result[a["_name"]][metric_name] = ((values[idx] - min_v) / range_v) * 100

    return result


def _build_bar_metrics(analyses):
    """Xây dựng dict metrics cho bar chart."""
    return {
        "Premium/Discount (%)": [a["premium_discount"]["percentage"] for a in analyses],
        "Đòn Bẩy Hiệu Dụng": [a["effective_leverage"] for a in analyses],
        "|Delta|": [abs(a["greeks"]["delta"]) for a in analyses],
        "HV Change (%)": [a["break_even_change_pct"] for a in analyses],
    }


def _format_date_vn(d):
    """Format ngày sang DD/MM/YYYY."""
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d)


def render_cw_compare_tab():
    """Tab 7: So sánh nhiều chứng quyền — chọn từ portfolio."""
    section_title("⇌", "So Sánh Chứng Quyền")

    st.markdown(
        '<div class="info-box">'
        'Chọn <b>2 đến 5 CW</b> từ portfolio để so sánh side-by-side. '
        'Thêm CW ở <b>Sidebar → Danh Sách CW Portfolio</b>.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Đọc portfolio từ session_state
    portfolio = st.session_state.get("cw_portfolio", [])

    if len(portfolio) < 2:
        tab_empty_state(
            "⇌",
            "Cần Ít Nhất 2 CW Để So Sánh",
            "Thêm CW ở Sidebar → Danh Sách CW Portfolio "
            "(thủ công hoặc upload CSV), sau đó quay lại tab này.",
            "Sidebar → Thêm CW hoặc Import CSV",
        )
        return

    # Multiselect chọn CW từ portfolio
    cw_options = []
    for idx, cw in enumerate(portfolio):
        loai = "CALL" if cw["option_type"] == "call" else "PUT"
        ma = cw.get("ma_cw", f"CW #{idx}")
        cs = cw.get("ma_co_so", "N/A")
        label = f"{ma} ({cs} | {loai} | S={format_vnd(cw['S'])} | K={format_vnd(cw['K'])})"
        cw_options.append(label)

    # Default: chọn tối đa 5 CW đầu tiên
    default_count = min(len(cw_options), 5)
    default_selection = cw_options[:default_count]

    selected_labels = st.multiselect(
        "Chọn 2-5 CW để so sánh",
        options=cw_options,
        default=default_selection,
        max_selections=5,
        help="Chọn tối thiểu 2, tối đa 5 CW từ portfolio",
    )

    if len(selected_labels) < 2:
        st.warning("Vui lòng chọn ít nhất **2 CW** để so sánh.")
        return

    # Map lại selected labels → cw_inputs
    cw_inputs = []
    for label in selected_labels:
        idx = cw_options.index(label)
        cw_inputs.append(portfolio[idx])

    # ===== PHÂN TÍCH =====
    section_divider(thick=True)

    analyses = []
    for cw in cw_inputs:
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
            result = analyzer.full_analysis()
            result["_input"] = cw
            result["_name"] = cw.get("ma_cw", "N/A")
            result["_error"] = None
            analyses.append(result)
        except Exception as e:
            analyses.append({
                "_input": cw,
                "_name": cw.get("ma_cw", "N/A"),
                "_error": str(e),
            })

    valid = [a for a in analyses if a["_error"] is None]
    errs = [a for a in analyses if a["_error"] is not None]

    for ea in errs:
        st.error(f"Lỗi phân tích **{ea['_name']}**: {ea['_error']}")

    if len(valid) < 2:
        st.warning("Cần ít nhất 2 CW phân tích thành công để so sánh.")
        return

    # ===== SO SÁNH SIDE-BY-SIDE =====
    section_title("▪", "So Sánh Các Chỉ Số Chính")

    cols = st.columns(len(valid))
    for idx, (col, a) in enumerate(zip(cols, valid)):
        cw = a["_input"]
        name = a["_name"]
        color = _get_cw_color(idx)
        pd_info = a["premium_discount"]

        with col:
            # Header card
            loai_label = "CALL" if cw["option_type"] == "call" else "PUT"
            st.markdown(
                f'<div class="cw-compare-header" style="border-top: 3px solid {color};">'
                f'<span style="color:{color};">{name}</span><br>'
                f'<small style="color:#718096;">{cw.get("ma_co_so", "N/A")} | '
                f'{loai_label}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Giá
            colored_metric("Giá CW Lý Thuyết", f"{format_vnd(a['theoretical_price'])} đ", color="#FF6B35")
            colored_metric("Giá CW Thị Trường", f"{format_vnd(cw['cw_price'])} đ", color="#F1F5F9")

            # Premium/Discount
            pd_color = (
                "#E74C3C" if pd_info["status"] == "Premium"
                else "#2ECC71" if pd_info["status"] == "Discount"
                else "#3B82F6"
            )
            colored_metric(
                "Premium/Discount",
                f"{pd_info['percentage']:+.2f}%",
                color=pd_color,
            )

            # Greeks
            colored_metric("Delta", f"{a['greeks']['delta']:.4f}", color="#4ECDC4")
            colored_metric("Gamma", f"{a['greeks']['gamma']:.6f}", color="#FF6B35")
            colored_metric("Theta", f"{a['greeks']['theta']:.4f}", color="#EF4444")

            # IV
            iv_str = format_pct(a["implied_volatility"] * 100) if a["implied_volatility"] else "N/A"
            colored_metric("Implied Volatility", iv_str, color="#A78BFA")

            # Leverage & Break-even
            colored_metric("Đòn Bẩy Hiệu Dụng", f"{a['effective_leverage']:.2f}x", color="#4ECDC4")
            colored_metric("Điểm Hoà Vốn", f"{format_vnd(a['break_even'])} đ", color="#F59E0B")
            colored_metric("Cần Đổi Để HV", format_pct(a["break_even_change_pct"]), color="#F59E0B")
            colored_metric("Moneyness", a["moneyness"], color="#93C5FD")
            days = cw['days_remaining']
            days_color = "#EF4444" if days < 30 else "#F59E0B" if days < 90 else "#22C55E"
            colored_metric("Ngày Còn Lại", f"{days} ngày", color=days_color)
            mat_date = cw.get("maturity_date", "N/A")
            colored_metric("Đáo Hạn", _format_date_vn(mat_date), color="#94A3B8")

    # ===== XẾP HẠNG =====
    section_divider()
    section_title("★", "Xếp Hạng & Khuyến Nghị")

    rankings = []
    for a in valid:
        rankings.append({
            "name": a["_name"],
            "premium_pct": abs(a["premium_discount"]["percentage"]),
            "premium_raw": a["premium_discount"]["percentage"],
            "eff_leverage": a["effective_leverage"],
            "delta_abs": abs(a["greeks"]["delta"]),
        })

    rec_cols = st.columns(4)

    with rec_cols[0]:
        best = min(rankings, key=lambda x: x["premium_pct"])
        st.markdown(
            f'<div class="cw-rank-card" style="border-top:3px solid #2ECC71;">'
            f'<div class="rank-title">Gần Giá Trị Hợp Lý Nhất</div>'
            f'<div class="rank-value" style="color:#2ECC71;">{best["name"]}</div>'
            f'<div class="rank-detail">|Premium| = {best["premium_pct"]:.2f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with rec_cols[1]:
        best = max(rankings, key=lambda x: x["eff_leverage"])
        st.markdown(
            f'<div class="cw-rank-card" style="border-top:3px solid #FF6B35;">'
            f'<div class="rank-title">Đòn Bẩy Cao Nhất</div>'
            f'<div class="rank-value" style="color:#FF6B35;">{best["name"]}</div>'
            f'<div class="rank-detail">Đòn bẩy = {best["eff_leverage"]:.2f}x</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with rec_cols[2]:
        best = min(rankings, key=lambda x: x["premium_raw"])
        label = "Rẻ Nhất (Discount)" if best["premium_raw"] < 0 else "Ít Đắt Nhất"
        st.markdown(
            f'<div class="cw-rank-card" style="border-top:3px solid #4ECDC4;">'
            f'<div class="rank-title">{label}</div>'
            f'<div class="rank-value" style="color:#4ECDC4;">{best["name"]}</div>'
            f'<div class="rank-detail">Premium = {best["premium_raw"]:+.2f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with rec_cols[3]:
        best = max(rankings, key=lambda x: x["delta_abs"])
        st.markdown(
            f'<div class="cw-rank-card" style="border-top:3px solid #A78BFA;">'
            f'<div class="rank-title">Delta Tốt Nhất</div>'
            f'<div class="rank-value" style="color:#A78BFA;">{best["name"]}</div>'
            f'<div class="rank-detail">|Delta| = {best["delta_abs"]:.4f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="warning-box">'
        '<b>△ Lưu ý:</b> Xếp hạng trên chỉ dựa trên từng tiêu chí riêng lẻ. '
        'Quyết định đầu tư cần xem xét tổng hợp nhiều yếu tố. '
        '<b>Đây không phải là khuyến nghị đầu tư.</b>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ===== BIỂU ĐỒ SO SÁNH =====
    section_divider()
    section_title("△", "Biểu Đồ So Sánh")

    chart_col1, chart_col2 = st.columns(2)

    cw_names = [a["_name"] for a in valid]

    with chart_col1:
        chart_container("Radar Chart Tổng Hợp")
        normalized = _normalize_metrics(valid)
        fig_radar = create_radar_chart(cw_names, normalized)
        st.plotly_chart(fig_radar, use_container_width=True)
        chart_container_end()

    with chart_col2:
        chart_container("So Sánh Chỉ Số Chính")
        metrics_dict = _build_bar_metrics(valid)
        fig_bar = create_comparison_bar_chart(cw_names, metrics_dict)
        st.plotly_chart(fig_bar, use_container_width=True)
        chart_container_end()

    # Overlaid payoff - full width
    section_divider()
    chart_container("Biểu Đồ Lãi/Lỗ Chồng Lấp")
    cw_payoff_data = []
    for a in valid:
        cw = a["_input"]
        cw_payoff_data.append({
            "name": a["_name"],
            "S": cw["S"],
            "K": cw["K"],
            "cw_price": cw["cw_price"],
            "cr": cw["cr"],
            "option_type": cw["option_type"],
        })
    fig_payoff = create_overlaid_payoff(cw_payoff_data)
    st.plotly_chart(fig_payoff, use_container_width=True)
    chart_container_end()

    # ===== BẢNG CHI TIẾT + EXPORT =====
    section_divider()
    section_title("≡", "Bảng So Sánh Chi Tiết")

    table_rows = []
    for a in valid:
        cw = a["_input"]
        pd_info = a["premium_discount"]
        iv_str = (
            format_pct(a["implied_volatility"] * 100)
            if a["implied_volatility"] else "N/A"
        )

        mat_date = cw.get("maturity_date", "N/A")

        table_rows.append({
            "Mã CW": a["_name"],
            "Mã CS": cw.get("ma_co_so", "N/A"),
            "Loại": "CALL" if cw["option_type"] == "call" else "PUT",
            "Giá CS (đ)": format_vnd(cw["S"]),
            "Strike (đ)": format_vnd(cw["K"]),
            "Giá CW TT (đ)": format_vnd(cw["cw_price"]),
            "Giá CW LT (đ)": format_vnd(a["theoretical_price"]),
            "Trạng Thái": pd_info["status_vi"],
            "P/D (%)": f"{pd_info['percentage']:+.2f}%",
            "Delta": f"{a['greeks']['delta']:.4f}",
            "Gamma": f"{a['greeks']['gamma']:.6f}",
            "Theta": f"{a['greeks']['theta']:.4f}",
            "Vega": f"{a['greeks']['vega']:.4f}",
            "IV": iv_str,
            "Đòn Bẩy": f"{a['effective_leverage']:.2f}x",
            "Gearing": f"{a['gearing']:.2f}x",
            "Hoà Vốn (đ)": format_vnd(a["break_even"]),
            "HV Change (%)": format_pct(a["break_even_change_pct"]),
            "Moneyness": a["moneyness"],
            "Đáo Hạn": _format_date_vn(mat_date),
            "Ngày Còn Lại": cw["days_remaining"],
            "Nội Tại (đ)": format_vnd(a["intrinsic_value"]),
            "Thời Gian (đ)": format_vnd(a["time_value"]),
        })

    result_df = pd.DataFrame(table_rows)
    table_container("Bảng So Sánh Chi Tiết", badge=f"{len(valid)} CW")
    st.dataframe(result_df, use_container_width=True, hide_index=True)
    table_container_end()

    # Export
    csv_data = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="↓ Tải Kết Quả So Sánh (CSV)",
        data=csv_data,
        file_name="so_sanh_chung_quyen.csv",
        mime="text/csv",
    )
