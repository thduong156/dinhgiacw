import math
import numpy as np
import streamlit as st
import pandas as pd
from core.warrant import WarrantAnalyzer
from core.markowitz import run_markowitz
from core.scoring import score_cw as _score_cw_core, grade_label as _grade_label_core
from ui.components import (
    format_vnd, format_pct, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end,
)
from ui.charts import (
    create_budget_pie_chart, create_budget_bar_chart,
    create_efficient_frontier_chart, create_weights_comparison_chart,
)


def _score_cw(analysis, days_remaining):
    """Delegate to core.scoring.score_cw (shared module)."""
    return _score_cw_core(analysis, days_remaining)


def _grade_label(score):
    """Delegate to core.scoring.grade_label (shared module)."""
    return _grade_label_core(score)


def render_recommend_tab():
    """Tab 8: Đề xuất CW tốt nhất — đọc trực tiếp từ portfolio."""
    section_title("★", "Đề Xuất Chứng Quyền Tốt Nhất")

    st.markdown(
        '<div class="info-box">'
        'Hệ thống <b>tự động phân tích & chấm điểm</b> tất cả CW trong portfolio. '
        'Thêm CW ở <b>Sidebar → Danh Sách CW Portfolio</b> '
        '(thủ công hoặc upload CSV). '
        'Cần ít nhất <b>2 CW</b> để đề xuất.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Đọc portfolio từ session_state
    portfolio = st.session_state.get("cw_portfolio", [])

    if len(portfolio) < 2:
        tab_empty_state(
            "★",
            "Cần Ít Nhất 2 CW Để Đề Xuất",
            f"Hiện có {len(portfolio)} CW trong portfolio. "
            "Thêm CW ở Sidebar → Danh Sách CW Portfolio "
            "(thủ công hoặc upload CSV).",
            "Sidebar → Thêm CW hoặc Import CSV",
        )
        return

    cw_inputs = portfolio

    # ===== PHÂN TÍCH & CHẤM ĐIỂM =====
    section_divider(thick=True)

    results = []
    for cw in cw_inputs:
        try:
            analyzer = WarrantAnalyzer(
                S=cw["S"], K=cw["K"], T=cw["T"], r=cw["r"], sigma=cw["sigma"],
                cw_market_price=cw["cw_price"], conversion_ratio=cw["cr"],
                option_type=cw["option_type"],
                q=cw.get("q", 0.0),
            )
            analysis = analyzer.full_analysis()
            total, breakdown = _score_cw(analysis, cw["days_remaining"])
            results.append({
                "name": cw.get("ma_cw", "N/A"),
                "input": cw,
                "analysis": analysis,
                "score": total,
                "breakdown": breakdown,
            })
        except Exception as e:
            st.error(f"Lỗi phân tích **{cw.get('ma_cw', 'N/A')}**: {e}")

    if len(results) < 2:
        st.warning("Cần ít nhất 2 CW phân tích thành công.")
        return

    # Sắp xếp theo điểm giảm dần
    results.sort(key=lambda x: x["score"], reverse=True)
    best = results[0]

    # ===== ĐỀ XUẤT SỐ 1 =====
    section_title("★", "Đề Xuất Tốt Nhất")

    grade_label, grade_color = _grade_label(best["score"])
    a = best["analysis"]
    inp = best["input"]
    pd_info = a["premium_discount"]
    pd_color = "#22C55E" if pd_info["percentage"] < 0 else "#EF4444"

    best_prob = a.get("probability_of_profit", 0)
    best_theta_eff = a.get("theta_efficiency", 0)
    best_issuer = inp.get("issuer", "—")
    best_te_txt = f"{best_theta_eff:.0f}d" if best_theta_eff < 999 else "∞"

    st.markdown(
        f'<div class="best-card" style="border:2px solid {grade_color};">'
        f'<div class="best-card-header">'
        f'<div class="best-card-score" style="color:{grade_color};">{best["score"]}</div>'
        f'<div>'
        f'<div class="best-card-name" style="color:{grade_color};">{best["name"]}</div>'
        f'<div class="best-card-meta">{grade_label} &bull; '
        f'{inp.get("ma_co_so", "N/A")} &bull; {inp["option_type"].upper()}'
        f'{" &bull; " + best_issuer if best_issuer not in ("—", "", None) else ""}</div>'
        f'</div></div>'
        f'<div class="best-card-grid">'
        f'<div class="best-card-stat">'
        f'<div class="best-card-stat-label">Giá LT</div>'
        f'<div class="best-card-stat-value" style="color:#F1F5F9;">'
        f'{format_vnd(a["theoretical_price"])} đ</div></div>'
        f'<div class="best-card-stat">'
        f'<div class="best-card-stat-label">P/D</div>'
        f'<div class="best-card-stat-value" style="color:{pd_color};">'
        f'{pd_info["percentage"]:+.1f}%</div></div>'
        f'<div class="best-card-stat">'
        f'<div class="best-card-stat-label">Đòn Bẩy</div>'
        f'<div class="best-card-stat-value" style="color:#4ECDC4;">'
        f'{a["effective_leverage"]:.1f}x</div></div>'
        f'<div class="best-card-stat">'
        f'<div class="best-card-stat-label">Delta</div>'
        f'<div class="best-card-stat-value" style="color:#A78BFA;">'
        f'{a["greeks"]["delta"]:.4f}</div></div>'
        f'<div class="best-card-stat">'
        f'<div class="best-card-stat-label">XS Lãi</div>'
        f'<div class="best-card-stat-value" style="color:#22C55E;">'
        f'{best_prob*100:.1f}%</div></div>'
        f'<div class="best-card-stat">'
        f'<div class="best-card-stat-label">Theta Eff</div>'
        f'<div class="best-card-stat-value" style="color:#F59E0B;">'
        f'{best_te_txt}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ===== PHÂN TÍCH CHI TIẾT CW SỐ 1 =====
    with st.expander("▪ Phân tích chi tiết CW được đề xuất", expanded=True):
        # Breakdown điểm — 7 tiêu chí
        st.markdown("**Điểm phân rã theo tiêu chí:**")
        max_scores = {"Định giá": 20, "Đòn bẩy": 15, "Delta": 15,
                      "Thời gian": 15, "Hoà vốn": 10, "Moneyness": 10, "Theta Eff": 15}
        breakdown_cols = st.columns(len(max_scores))
        for idx, (criteria, max_s) in enumerate(max_scores.items()):
            val = best["breakdown"].get(criteria, 0)
            pct = val / max_s * 100 if max_s > 0 else 0
            c_color = "#22C55E" if pct >= 70 else "#F59E0B" if pct >= 40 else "#EF4444"
            with breakdown_cols[idx]:
                st.markdown(
                    f'<div class="score-card">'
                    f'<div class="score-card-label">{criteria}</div>'
                    f'<div class="score-card-value" style="color:{c_color};">'
                    f'{val}/{max_s}</div>'
                    f'<div class="score-card-bar">'
                    f'<div class="score-card-bar-fill" style="width:{pct}%; '
                    f'background:{c_color};"></div></div></div>',
                    unsafe_allow_html=True,
                )

        section_divider()

        # Greeks + chỉ số
        g_cols = st.columns(4)
        with g_cols[0]:
            colored_metric("Giá Lý Thuyết", f"{format_vnd(a['theoretical_price'])} đ", "#F1F5F9")
        with g_cols[1]:
            iv = a.get("implied_volatility")
            iv_text = f"{iv*100:.1f}%" if iv else "N/A"
            colored_metric("IV (Ngầm Định)", iv_text, "#A78BFA")
        with g_cols[2]:
            colored_metric("Hoà Vốn", f"{format_vnd(a['break_even'])} đ", "#4ECDC4")
        with g_cols[3]:
            colored_metric("Gearing", f"{a['gearing']:.2f}x", "#FF6B35")

        # Lý do đề xuất
        section_divider()
        reasons = []
        if pd_info["percentage"] < -3:
            reasons.append(f"✓ Đang Discount {pd_info['percentage']:+.1f}% — giá thấp hơn giá trị thực")
        if best_prob > 0.4:
            reasons.append(f"✓ Xác suất lãi {best_prob*100:.0f}% — khả năng sinh lời tốt")
        if a["effective_leverage"] >= 3:
            reasons.append(f"✓ Đòn bẩy hiệu dụng {a['effective_leverage']:.1f}x — khuếch đại tốt")
        if abs(a["greeks"]["delta"]) >= 0.3:
            reasons.append(f"✓ Delta {a['greeks']['delta']:.4f} — nhạy cảm với giá cơ sở")
        if inp["days_remaining"] > 90:
            reasons.append(f"✓ Còn {inp['days_remaining']} ngày — thời gian thoải mái")
        if best_theta_eff > 80:
            reasons.append(f"✓ Theta Efficiency {best_theta_eff:.0f} ngày — time decay thấp")
        if abs(a["break_even_change_pct"]) <= 10:
            reasons.append(f"✓ Hoà vốn gần — chỉ cần thay đổi {abs(a['break_even_change_pct']):.1f}%")

        if reasons:
            st.markdown(
                '<div class="success-box"><b>Lý do đề xuất:</b><br>'
                + "<br>".join(reasons)
                + '</div>',
                unsafe_allow_html=True,
            )

        # Cảnh báo
        warnings = []
        if pd_info["percentage"] > 10:
            warnings.append(f"△ Premium cao {pd_info['percentage']:+.1f}%")
        if inp["days_remaining"] < 60:
            warnings.append(f"△ Thời gian ngắn — còn {inp['days_remaining']} ngày")
        if a["effective_leverage"] > 10:
            warnings.append(f"△ Đòn bẩy rất cao {a['effective_leverage']:.1f}x — rủi ro lớn")

        if warnings:
            st.markdown(
                '<div class="warning-box"><b>Lưu ý:</b><br>'
                + "<br>".join(warnings)
                + '</div>',
                unsafe_allow_html=True,
            )

    # ===== SO SÁNH TOP 3 =====
    if len(results) >= 3:
        section_divider()
        section_title("★", "Top 3 CW Được Đề Xuất")

        top3_cols = st.columns(3)
        medals = ["I", "II", "III"]
        medal_colors = ["#FFD700", "#C0C0C0", "#CD7F32"]

        for idx in range(3):
            r = results[idx]
            a = r["analysis"]
            inp = r["input"]
            grade, g_color = _grade_label(r["score"])
            pd_i = a["premium_discount"]
            pd_c = "#22C55E" if pd_i["percentage"] < 0 else "#EF4444"
            m_prob = a.get("probability_of_profit", 0)
            m_te = a.get("theta_efficiency", 0)
            m_te_txt = f"{m_te:.0f}d" if m_te < 999 else "∞"

            with top3_cols[idx]:
                st.markdown(
                    f'<div class="medal-card" style="border:2px solid {medal_colors[idx]};">'
                    f'<div class="medal-card-icon">{medals[idx]}</div>'
                    f'<div class="medal-card-name" style="color:{medal_colors[idx]};">{r["name"]}</div>'
                    f'<div class="medal-card-score" style="color:{g_color};">'
                    f'{r["score"]}<span style="font-size:0.8rem; color:#64748B;">/100</span></div>'
                    f'<div class="medal-card-grade">{grade}</div>'
                    f'<div class="medal-card-grid">'
                    f'<div class="medal-card-grid-label">P/D</div>'
                    f'<div class="medal-card-grid-value" style="color:{pd_c};">'
                    f'{pd_i["percentage"]:+.1f}%</div>'
                    f'<div class="medal-card-grid-label">XS Lãi</div>'
                    f'<div class="medal-card-grid-value" style="color:#22C55E;">'
                    f'{m_prob*100:.0f}%</div>'
                    f'<div class="medal-card-grid-label">Đòn bẩy</div>'
                    f'<div class="medal-card-grid-value" style="color:#4ECDC4;">'
                    f'{a["effective_leverage"]:.1f}x</div>'
                    f'<div class="medal-card-grid-label">Theta Eff</div>'
                    f'<div class="medal-card-grid-value" style="color:#F59E0B;">'
                    f'{m_te_txt}</div>'
                    f'<div class="medal-card-grid-label">Delta</div>'
                    f'<div class="medal-card-grid-value" style="color:#A78BFA;">'
                    f'{a["greeks"]["delta"]:.4f}</div>'
                    f'<div class="medal-card-grid-label">Còn lại</div>'
                    f'<div class="medal-card-grid-value" style="color:#F1F5F9;">'
                    f'{inp["days_remaining"]}d</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

    # ===== BẢNG XẾP HẠNG TOÀN BỘ =====
    section_divider()
    section_title("≡", "Bảng Xếp Hạng Toàn Bộ")

    table_rows = []
    for rank, r in enumerate(results, 1):
        a = r["analysis"]
        inp = r["input"]
        grade, g_color = _grade_label(r["score"])
        pd_i = a["premium_discount"]
        iv = a.get("implied_volatility")
        iv_str = f"{iv*100:.1f}%" if iv else "N/A"
        prob_p = a.get("probability_of_profit", 0)
        te = a.get("theta_efficiency", 0)
        te_str = f"{te:.0f}d" if te < 999 else "∞"

        table_rows.append({
            "Hạng": f"#{rank}",
            "Mã CW": r["name"],
            "TCPH": inp.get("issuer", "—"),
            "Mã CS": inp.get("ma_co_so", "N/A"),
            "Điểm": r["score"],
            "Xếp Loại": grade,
            "Giá CW (đ)": format_vnd(inp["cw_price"]),
            "Giá LT (đ)": format_vnd(a["theoretical_price"]),
            "P/D (%)": f"{pd_i['percentage']:+.1f}%",
            "XS Lãi": f"{prob_p*100:.1f}%",
            "Đòn Bẩy": f"{a['effective_leverage']:.1f}x",
            "Delta": f"{a['greeks']['delta']:.4f}",
            "Theta Eff": te_str,
            "IV": iv_str,
            "Ngày Còn Lại": inp["days_remaining"],
            "Moneyness": a["moneyness"],
            # Breakdown — 7 tiêu chí mới
            "Đ.Giá": f"{r['breakdown'].get('Định giá', 0)}/20",
            "Đ.Bẩy": f"{r['breakdown'].get('Đòn bẩy', 0)}/15",
            "Đ.Delta": f"{r['breakdown'].get('Delta', 0)}/15",
            "Đ.TG": f"{r['breakdown'].get('Thời gian', 0)}/15",
            "Đ.HV": f"{r['breakdown'].get('Hoà vốn', 0)}/10",
            "Đ.Money": f"{r['breakdown'].get('Moneyness', 0)}/10",
            "Đ.Theta": f"{r['breakdown'].get('Theta Eff', 0)}/15",
        })

    result_df = pd.DataFrame(table_rows)
    table_container("Bảng Xếp Hạng Toàn Bộ", badge=f"{len(results)} CW")
    st.dataframe(result_df, use_container_width=True, hide_index=True)
    table_container_end()

    # Export
    csv_data = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="↓ Tải Bảng Xếp Hạng (CSV)",
        data=csv_data,
        file_name="de_xuat_chung_quyen.csv",
        mime="text/csv",
        key="rec_download",
    )

    # ===== PHÂN BỔ NGÂN SÁCH ĐẦU TƯ =====
    section_divider(thick=True)
    _render_budget_allocation(results)

    # Disclaimer
    section_divider()
    st.markdown(
        '<div class="warning-box">'
        '<b>△ Lưu ý quan trọng:</b> Đề xuất dựa trên mô hình Black-Scholes '
        'và các tiêu chí định lượng. <b>Đây không phải là khuyến nghị đầu tư.</b> '
        'Nhà đầu tư cần xem xét thêm: thanh khoản, xu hướng cổ phiếu cơ sở, '
        'tin tức thị trường, và khẩu vị rủi ro cá nhân trước khi quyết định.'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# PHÂN BỔ NGÂN SÁCH ĐẦU TƯ — MARKOWITZ OPTIMIZATION
# ============================================================

def _render_budget_allocation(results):
    """
    Phân bổ ngân sách đầu tư cho portfolio CW bằng Markowitz.
    results: danh sách đã sorted theo score (từ render_recommend_tab).
    """
    section_title("◈", "Phân Bổ Ngân Sách Đầu Tư — Markowitz")

    st.markdown(
        '<div class="info-box">'
        'Hệ thống sử dụng <b>Mô hình Markowitz (Mean-Variance Optimization)</b> '
        'để tìm danh mục tối ưu. '
        'Tỷ trọng được tính dựa trên <b>kỳ vọng lợi nhuận</b>, '
        '<b>rủi ro</b>, và <b>tương quan</b> giữa các CW.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Chạy Markowitz optimization ---
    try:
        mkz = run_markowitz(results)
    except Exception as e:
        st.error(f"Lỗi khi chạy Markowitz optimization: {e}")
        return

    assets = mkz["assets"]
    excluded = mkz["excluded_assets"]
    frontier = mkz["frontier"]
    included_indices = mkz["included_indices"]
    data_sources = mkz.get("data_sources", {})

    # --- Hiển thị nguồn dữ liệu (Real vs Estimated) ---
    real_count = sum(1 for v in data_sources.values() if v == "real")
    est_count = sum(1 for v in data_sources.values() if v == "estimated")

    if real_count > 0:
        source_html = (
            '<div style="margin:8px 0 12px 0;">'
            '<span style="font-size:0.78rem; color:#94A3B8; margin-right:8px;">Nguồn dữ liệu:</span>'
            f'<span class="data-source-badge real">▪ DỮ LIỆU THỰC</span> '
            f'<span style="font-size:0.75rem; color:#94A3B8;">{real_count} CW</span>'
            f'&nbsp;&nbsp;'
            f'<span class="data-source-badge estimated">∠ ƯỚC TÍNH</span> '
            f'<span style="font-size:0.75rem; color:#94A3B8;">{est_count} CW</span>'
            '</div>'
        )
    else:
        source_html = (
            '<div style="margin:8px 0 12px 0;">'
            '<span class="data-source-badge estimated">∠ ƯỚC TÍNH</span> '
            '<span style="font-size:0.75rem; color:#94A3B8;">Tất cả dữ liệu đang được ước tính. '
            'Thêm dữ liệu hàng ngày ở Tab '
            '<b>"⊡ Theo Dõi Hàng Ngày"</b> để cải thiện độ chính xác.</span>'
            '</div>'
        )
    st.markdown(source_html, unsafe_allow_html=True)

    # --- Hiển thị CW bị loại khỏi phân bổ ---
    if excluded:
        excluded_names = ", ".join([f"**{a.name}** (KV: {a.expected_return*100:+.1f}%)" for a in excluded])
        st.markdown(
            f'<div class="warning-box">'
            f'<b>△ CW bị loại khỏi phân bổ ngân sách:</b> {excluded_names}<br>'
            f'<small>Lý do: Kỳ vọng lợi nhuận quá âm (< -5%). '
            f'CW đang Premium cao hoặc gần hết hạn — khả năng lỗ vốn lớn. '
            f'Markowitz chỉ tối ưu trên các CW còn tiềm năng sinh lời.</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- PHẦN 1: Efficient Frontier ---
    section_title("△", "Efficient Frontier")

    fig_frontier = create_efficient_frontier_chart(
        frontier, assets,
        mkz["max_sharpe_metrics"], mkz["min_var_metrics"],
        mkz["max_sharpe_weights"], mkz["min_var_weights"],
    )
    chart_container("Efficient Frontier")
    st.plotly_chart(fig_frontier, use_container_width=True)
    chart_container_end()

    # Metrics: 2 portfolio tối ưu
    ms = mkz["max_sharpe_metrics"]   # (return, vol, sharpe)
    mv = mkz["min_var_metrics"]

    col_ms, col_mv = st.columns(2)
    with col_ms:
        st.markdown(
            f'<div class="scenario-card scenario-card-gold">'
            f'<h4 style="color:#FFD700;">★ Max Sharpe Ratio</h4>'
            f'<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px;">'
            f'<div><div style="font-size:0.7rem; color:#94A3B8;">Lợi Nhuận KV</div>'
            f'<div style="font-size:1.1rem; color:#22C55E; font-weight:700;">{ms[0]*100:+.1f}%</div></div>'
            f'<div><div style="font-size:0.7rem; color:#94A3B8;">Rủi Ro (Vol)</div>'
            f'<div style="font-size:1.1rem; color:#F59E0B; font-weight:700;">{ms[1]*100:.1f}%</div></div>'
            f'<div><div style="font-size:0.7rem; color:#94A3B8;">Sharpe Ratio</div>'
            f'<div style="font-size:1.1rem; color:#FFD700; font-weight:700;">{ms[2]:.3f}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with col_mv:
        st.markdown(
            f'<div class="scenario-card scenario-card-teal">'
            f'<h4 style="color:#4ECDC4;">◇ Min Variance (Rủi Ro Thấp Nhất)</h4>'
            f'<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px;">'
            f'<div><div style="font-size:0.7rem; color:#94A3B8;">Lợi Nhuận KV</div>'
            f'<div style="font-size:1.1rem; color:#22C55E; font-weight:700;">{mv[0]*100:+.1f}%</div></div>'
            f'<div><div style="font-size:0.7rem; color:#94A3B8;">Rủi Ro (Vol)</div>'
            f'<div style="font-size:1.1rem; color:#F59E0B; font-weight:700;">{mv[1]*100:.1f}%</div></div>'
            f'<div><div style="font-size:0.7rem; color:#94A3B8;">Sharpe Ratio</div>'
            f'<div style="font-size:1.1rem; color:#4ECDC4; font-weight:700;">{mv[2]:.3f}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # --- So sánh tỷ trọng ---
    section_divider()
    asset_names = [a.name for a in assets]
    chart_container("So Sánh Tỷ Trọng")
    fig_weights = create_weights_comparison_chart(
        asset_names, mkz["max_sharpe_weights"], mkz["min_var_weights"],
    )
    st.plotly_chart(fig_weights, use_container_width=True)
    chart_container_end()

    # --- Bảng Return/Risk từng CW (bao gồm CW tham gia + bị loại) ---
    section_divider()
    section_title("▪", "Kỳ Vọng & Rủi Ro Từng CW")

    asset_rows = []
    # CW tham gia tối ưu
    for i, a in enumerate(assets):
        src = data_sources.get(a.name, "estimated")
        src_label = "▪ Thực" if src == "real" else "∠ Ước tính"
        asset_rows.append({
            "Mã CW": a.name,
            "Cổ Phiếu CS": a.ma_co_so,
            "Loại": a.option_type.upper(),
            "Điểm": a.score,
            "Kỳ Vọng LN": f"{a.expected_return*100:+.1f}%",
            "Rủi Ro (σ)": f"{a.volatility*100:.1f}%",
            "Nguồn DL": src_label,
            "Giá CW (đ)": format_vnd(a.cw_price),
            "W. Max Sharpe": f"{mkz['max_sharpe_weights'][i]*100:.1f}%",
            "W. Min Var": f"{mkz['min_var_weights'][i]*100:.1f}%",
            "Trạng Thái": "✓ Tham gia",
        })
    # CW bị loại
    for a in excluded:
        src = data_sources.get(a.name, "estimated")
        src_label = "▪ Thực" if src == "real" else "∠ Ước tính"
        asset_rows.append({
            "Mã CW": a.name,
            "Cổ Phiếu CS": a.ma_co_so,
            "Loại": a.option_type.upper(),
            "Điểm": a.score,
            "Kỳ Vọng LN": f"{a.expected_return*100:+.1f}%",
            "Rủi Ro (σ)": f"{a.volatility*100:.1f}%",
            "Nguồn DL": src_label,
            "Giá CW (đ)": format_vnd(a.cw_price),
            "W. Max Sharpe": "—",
            "W. Min Var": "—",
            "Trạng Thái": "× Loại (KV âm)",
        })
    table_container("Kỳ Vọng & Rủi Ro Từng CW", badge=f"{len(asset_rows)} CW")
    st.dataframe(pd.DataFrame(asset_rows), use_container_width=True, hide_index=True)
    table_container_end()

    # --- PHẦN 2: Phân bổ ngân sách ---
    section_divider(thick=True)
    section_title("◈", "Phân Bổ Ngân Sách Thực Tế")

    col_budget, col_strategy = st.columns([1.5, 1])

    with col_budget:
        budget_raw = st.text_input(
            "◆ Tổng Ngân Sách (VNĐ)",
            value="10,000,000",
            key="budget_input",
            help="Nhập số tiền bạn muốn đầu tư vào portfolio CW",
        )
        cleaned = (budget_raw.replace(",", "").replace(".", "")
                   .replace(" ", "").replace("đ", "").strip())
        try:
            budget = float(cleaned)
            if budget < 0:
                budget = 0
        except (ValueError, TypeError):
            budget = 10_000_000

    with col_strategy:
        strategy = st.selectbox(
            "▪ Danh Mục Markowitz",
            options=["Max Sharpe Ratio", "Min Variance"],
            key="budget_strategy",
            help=(
                "Max Sharpe: Tối đa hoá lợi nhuận/rủi ro. "
                "Min Variance: Tối thiểu hoá rủi ro."
            ),
        )

    if budget <= 0:
        st.warning("Vui lòng nhập ngân sách lớn hơn 0.")
        return

    # Lấy weights theo chiến lược
    if strategy == "Max Sharpe Ratio":
        weights = mkz["max_sharpe_weights"]
        port_metrics = mkz["max_sharpe_metrics"]
    else:
        weights = mkz["min_var_weights"]
        port_metrics = mkz["min_var_metrics"]

    # --- Tính phân bổ chi tiết (chỉ cho CW tham gia, không phân bổ cho CW bị loại) ---
    allocations = []
    total_allocated = 0
    total_qty = 0

    for i, (asset, w) in enumerate(zip(assets, weights)):
        # Lấy result gốc tương ứng qua included_indices
        orig_idx = included_indices[i]
        r = results[orig_idx]

        cw_price = r["input"]["cw_price"]
        if cw_price <= 0:
            continue

        alloc_amount = budget * w
        qty = math.floor(alloc_amount / cw_price)
        actual_cost = qty * cw_price

        theo_price = r["analysis"]["theoretical_price"]
        expected_pnl = (theo_price - cw_price) * qty if qty > 0 else 0
        expected_pnl_pct = ((theo_price / cw_price) - 1) * 100 if cw_price > 0 else 0

        allocations.append({
            "name": r["name"],
            "score": r["score"],
            "weight": w,
            "pct": w * 100,
            "target_amount": alloc_amount,
            "qty": qty,
            "amount": actual_cost,
            "cw_price": cw_price,
            "theo_price": theo_price,
            "expected_pnl": expected_pnl,
            "expected_pnl_pct": expected_pnl_pct,
            "eff_leverage": r["analysis"]["effective_leverage"],
            "days_remaining": r["input"]["days_remaining"],
            "exp_return": asset.expected_return,
            "cw_vol": asset.volatility,
        })
        total_allocated += actual_cost
        total_qty += qty

    remaining = budget - total_allocated

    # --- Metrics tổng quan ---
    section_divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        colored_metric("Tổng Ngân Sách", f"{format_vnd(budget)} đ", color="#FF6B35")
    with m2:
        colored_metric("Đã Phân Bổ", f"{format_vnd(total_allocated)} đ", color="#4ECDC4")
    with m3:
        colored_metric("Còn Lại", f"{format_vnd(remaining)} đ", color="#F59E0B")
    with m4:
        colored_metric("Tổng SL CW", f"{total_qty:,}", color="#A78BFA")
    with m5:
        colored_metric("Sharpe Ratio", f"{port_metrics[2]:.3f}", color="#FFD700")

    # --- Biểu đồ phân bổ ---
    section_divider()
    valid_allocs = [a for a in allocations if a["qty"] > 0]

    if valid_allocs:
        col_pie, col_bar = st.columns(2)
        with col_pie:
            chart_container("Tỷ Trọng Phân Bổ")
            fig_pie = create_budget_pie_chart(valid_allocs)
            st.plotly_chart(fig_pie, use_container_width=True)
            chart_container_end()
        with col_bar:
            chart_container("Chi Phí Phân Bổ")
            fig_bar = create_budget_bar_chart(valid_allocs)
            st.plotly_chart(fig_bar, use_container_width=True)
            chart_container_end()
    else:
        st.warning(
            "Ngân sách quá nhỏ — không đủ mua được CW nào. "
            "Vui lòng tăng ngân sách."
        )
        return

    # --- Bảng chi tiết phân bổ ---
    section_divider()
    section_title("≡", "Chi Tiết Phân Bổ")

    table_rows = []
    for idx, a in enumerate(allocations, 1):
        pnl_icon = "🟢" if a["expected_pnl"] >= 0 else "🔴"
        grade, _ = _grade_label(a["score"])
        table_rows.append({
            "#": idx,
            "Mã CW": a["name"],
            "Điểm": a["score"],
            "Tỷ Trọng": f"{a['pct']:.1f}%",
            "Giá CW (đ)": format_vnd(a["cw_price"]),
            "Số Lượng": f"{a['qty']:,}",
            "Chi Phí (đ)": format_vnd(a["amount"]),
            "KV LN": f"{a['exp_return']*100:+.1f}%",
            "Rủi Ro": f"{a['cw_vol']*100:.1f}%",
            f"{pnl_icon} L/L KV (đ)": f"{a['expected_pnl']:+,.0f}",
            "Đòn Bẩy": f"{a['eff_leverage']:.1f}x",
            "Ngày Còn": a["days_remaining"],
        })

    alloc_df = pd.DataFrame(table_rows)
    table_container("Chi Tiết Phân Bổ", badge=f"{len(allocations)} CW")
    st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    table_container_end()

    # --- Tổng kết portfolio ---
    total_expected_pnl = sum(a["expected_pnl"] for a in allocations)
    total_expected_pnl_pct = (total_expected_pnl / total_allocated * 100
                              if total_allocated > 0 else 0)
    pnl_box_class = "success-box" if total_expected_pnl >= 0 else "danger-box"
    pnl_label = "LỜI" if total_expected_pnl >= 0 else "LỖ"

    st.markdown(
        f'<div class="{pnl_box_class}">'
        f'<b>Danh Mục Tối Ưu ({strategy}):</b> '
        f'Kỳ vọng {pnl_label} <b>{format_vnd(abs(total_expected_pnl))} đ</b> '
        f'(<b>{total_expected_pnl_pct:+.1f}%</b>)<br>'
        f'<small>KV Lợi Nhuận Portfolio: <b>{port_metrics[0]*100:+.1f}%</b> | '
        f'Rủi Ro Portfolio: <b>{port_metrics[1]*100:.1f}%</b> | '
        f'Sharpe Ratio: <b>{port_metrics[2]:.3f}</b></small>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Export ---
    csv_alloc = alloc_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="↓ Tải Phân Bổ Ngân Sách (CSV)",
        data=csv_alloc,
        file_name="phan_bo_ngan_sach_markowitz.csv",
        mime="text/csv",
        key="budget_download",
    )

    # --- Correlation Matrix ---
    with st.expander("⊞ Ma Trận Tương Quan (Correlation Matrix)", expanded=False):
        corr = mkz["corr_matrix"]
        corr_df = pd.DataFrame(
            np.round(corr, 2),
            index=asset_names,
            columns=asset_names,
        )
        table_container("Correlation Matrix", badge=f"{len(asset_names)}x{len(asset_names)}")
        st.dataframe(corr_df, use_container_width=True)
        table_container_end()
        corr_note = (
            'Tương quan được tính từ <b>dữ liệu thực tế</b> khi có đủ lịch sử '
            '(≥ 5 ngày chồng lấp). '
            'Các cặp thiếu dữ liệu sử dụng proxy: '
            'cùng CS/cùng loại ≈ 0.90, cùng CS/khác loại ≈ -0.70, '
            'khác CS ≈ 0.30.'
        ) if real_count > 0 else (
            'Tương quan được ước tính dựa trên cổ phiếu cơ sở và loại CW '
            '(cùng CS/cùng loại ≈ 0.90, cùng CS/khác loại ≈ -0.70, '
            'khác CS ≈ 0.30).'
        )
        st.markdown(
            f'<div style="font-size:0.75rem; color:#64748B; margin-top:4px;">'
            f'{corr_note}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Giải thích Markowitz ---
    with st.expander("○ Về Mô Hình Markowitz", expanded=False):
        st.markdown(
            "### Modern Portfolio Theory (MPT)\n\n"
            "**Harry Markowitz** (Nobel 1990) đề xuất rằng nhà đầu tư "
            "nên chọn danh mục dựa trên **tổng thể portfolio** thay vì "
            "từng tài sản riêng lẻ.\n\n"
            "**Nguyên lý chính:**\n"
            "- **Đa dạng hoá** giảm rủi ro mà không nhất thiết giảm lợi nhuận\n"
            "- Mỗi portfolio nằm trên không gian Return-Risk\n"
            "- **Efficient Frontier** là tập hợp các danh mục tối ưu\n\n"
            "**2 danh mục tối ưu:**\n"
            "- **Max Sharpe Ratio**: Tối đa hoá (Return - Risk-free) / Risk. "
            "Phù hợp cho nhà đầu tư cân bằng giữa lợi nhuận và rủi ro.\n"
            "- **Min Variance**: Tối thiểu hoá rủi ro. "
            "Phù hợp cho nhà đầu tư ưu tiên bảo toàn vốn.\n\n"
            "**Nguồn dữ liệu:**\n"
            "- ▪ **Dữ liệu thực**: Khi có ≥ 5 ngày lịch sử từ Tab "
            "\"Theo Dõi Hàng Ngày\", hệ thống dùng actual returns & volatility\n"
            "- ∠ **Ước tính**: Expected Return dựa trên convergence giá LT↔TT "
            "và effective leverage × equity premium; "
            "Volatility = IV × leverage × √T\n"
            "- *Correlation*: Thực tế khi có dữ liệu chồng lấp, "
            "proxy từ cùng/khác cổ phiếu cơ sở khi không có\n\n"
            "△ **Lưu ý**: Nhập dữ liệu hàng ngày giúp cải thiện "
            "đáng kể độ chính xác của mô hình. "
            "Kết quả chỉ mang tính tham khảo."
        )
