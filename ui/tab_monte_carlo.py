"""
Tab Mô Phỏng Monte Carlo — Danh Mục hoặc CW Đơn Lẻ.

Hỗ trợ 2 chế độ:
  - Toàn bộ danh mục (correlated GBM cho nhiều underlying)
  - CW đơn lẻ (GBM cho 1 underlying duy nhất)
"""

import hashlib
import numpy as np
import streamlit as st
import pandas as pd
from core.monte_carlo import simulate_portfolio
from ui.components import (
    format_vnd, section_title, colored_metric,
    section_divider, chart_container, chart_container_end,
    table_container, table_container_end, render_table,
)
from ui.charts import (
    create_mc_fan_chart,
    create_mc_distribution,
    create_mc_contribution,
)

# ── Constants ─────────────────────────────────────────────────
_PATH_OPTIONS = {
    "1,000 paths (nhanh)":         1_000,
    "5,000 paths":                 5_000,
    "10,000 paths":               10_000,
    "50,000 paths (chính xác)":   50_000,
}
_CONF_OPTIONS = {"90%": 0.90, "95%": 0.95, "99%": 0.99}


# ============================================================
# MAIN RENDER
# ============================================================

def render_monte_carlo_tab():
    """Tab 10: Mô Phỏng Monte Carlo."""
    section_title("∿", "Mô Phỏng Monte Carlo")

    st.markdown(
        '<div class="info-box">'
        '<b>Monte Carlo</b> mô phỏng hàng nghìn kịch bản giá ngẫu nhiên theo '
        '<b>Geometric Brownian Motion</b>, cho biết <b>phân phối lãi/lỗ</b> thực sự '
        '— không chỉ là kịch bản lạc quan hay bi quan đơn lẻ.<br>'
        'Chọn mô phỏng <b>toàn bộ danh mục</b> (có tương quan) hoặc <b>CW đơn lẻ</b>.'
        '</div>',
        unsafe_allow_html=True,
    )

    portfolio = st.session_state.get("cw_portfolio", [])

    if not portfolio:
        st.markdown(
            '<div class="warning-box">'
            '▣ Chưa có CW nào trong danh mục. '
            'Thêm CW ở <b>Thanh bên → Danh Sách CW Portfolio</b>.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Chế độ: Danh mục vs CW đơn lẻ ────────────────────────
    mode_col, target_col = st.columns([1, 2])

    with mode_col:
        mode = st.radio(
            "⊕ Phạm Vi Mô Phỏng",
            options=["▣ Toàn bộ danh mục", "◎ CW đơn lẻ"],
            key="mc_mode",
            horizontal=True,
        )

    is_single = mode.startswith("◎")

    # Xác định danh sách CW sẽ chạy simulation
    selected_idx = None
    if is_single:
        cw_names = [
            f"{cw.get('ma_cw', f'CW #{i}')} ({cw.get('ma_co_so', '?')})"
            for i, cw in enumerate(portfolio)
        ]
        with target_col:
            selected_idx = st.selectbox(
                "▪ Chọn CW",
                options=range(len(portfolio)),
                format_func=lambda i: cw_names[i],
                key="mc_single_cw",
            )
        sim_portfolio = [portfolio[selected_idx]]
        sim_label = portfolio[selected_idx].get("ma_cw", f"CW #{selected_idx}")
    else:
        sim_portfolio = portfolio
        sim_label = f"Danh mục ({len(portfolio)} CW)"

    # ── Controls ──────────────────────────────────────────────
    cc1, cc2, cc3 = st.columns([1.4, 2, 1])

    with cc1:
        paths_label = st.selectbox(
            "▪ Số Mô Phỏng",
            options=list(_PATH_OPTIONS.keys()),
            index=1,
            key="mc_n_paths",
        )
        n_paths = _PATH_OPTIONS[paths_label]

    with cc2:
        max_days = _max_holding_days(sim_portfolio)
        holding_days = st.slider(
            "⊡ Số Ngày Giữ",
            min_value=1, max_value=max_days,
            value=min(30, max_days),
            step=1, key="mc_holding_days",
        )

    with cc3:
        conf_label = st.radio(
            "⊕ Độ Tin Cậy VaR",
            options=list(_CONF_OPTIONS.keys()),
            index=1,
            key="mc_conf",
            horizontal=False,
        )
        confidence_level = _CONF_OPTIONS[conf_label]

    # ── Nút chạy ─────────────────────────────────────────────
    run_key = _cache_key(sim_portfolio, n_paths, holding_days, confidence_level, mode)
    already_run = (
        "_mc_result" in st.session_state
        and st.session_state.get("_mc_run_key") == run_key
    )

    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        run_clicked = st.button(
            "▶ Chạy Mô Phỏng" if not already_run else "↻ Chạy Lại",
            use_container_width=True,
            key="mc_run_btn",
            type="primary",
        )
    with col_hint:
        if already_run:
            st.caption(
                f"✓ **{sim_label}** · {n_paths:,} paths · "
                f"{holding_days} ngày · VaR {conf_label}"
            )

    if run_clicked or already_run:
        if run_clicked:
            with st.spinner(f"⧖ Đang mô phỏng {sim_label} — {n_paths:,} paths..."):
                result = simulate_portfolio(
                    portfolio=sim_portfolio,
                    n_paths=n_paths,
                    holding_days=holding_days,
                    confidence_level=confidence_level,
                )
            st.session_state["_mc_result"] = result
            st.session_state["_mc_run_key"] = run_key
        else:
            result = st.session_state["_mc_result"]

        _render_results(result, conf_label, confidence_level, is_single, sim_label)


# ============================================================
# RENDER RESULTS
# ============================================================

def _render_results(
    result: dict,
    conf_label: str,
    confidence_level: float,
    is_single: bool,
    sim_label: str,
):
    """Hiển thị toàn bộ kết quả simulation."""
    stats = result["stats"]
    per_cw = result["per_cw"]
    fallback = result["fallback_mode"]

    if fallback:
        st.markdown(
            '<div class="warning-box">'
            '△ CW chưa có vị thế (số lượng + giá vào). '
            'Đang mô phỏng với <b>1 đơn vị</b>, giá vào = giá hiện tại.'
            '</div>',
            unsafe_allow_html=True,
        )

    section_divider()

    # ── 1. Bảng CW tham gia ───────────────────────────────────
    _render_portfolio_table(result, is_single, sim_label)

    section_divider()

    # ── 2. Fan chart ──────────────────────────────────────────
    fan_title = f"Hành Trình PnL — {sim_label}" if is_single else "Hành Trình PnL Danh Mục"
    section_title("△", fan_title)
    chart_container()
    fig_fan = create_mc_fan_chart(
        days=result["days"],
        percentiles=result["percentiles"],
        baseline=result["pnl_baseline"],
        initial_pnl=0.0,
    )
    st.plotly_chart(fig_fan, use_container_width=True)
    chart_container_end()
    st.caption(
        "**Vùng đậm**: 25th – 75th percentile &nbsp;|&nbsp; "
        "**Vùng nhạt**: 5th – 95th percentile &nbsp;|&nbsp; "
        "**Đường xanh**: Trung vị &nbsp;|&nbsp; "
        "**Đường cam nét đứt**: Baseline (giá không đổi, chỉ time decay)"
    )

    section_divider()

    # ── 3. Histogram + Risk Metrics ───────────────────────────
    section_title("▪", "Phân Phối PnL Cuối Kỳ & Chỉ Số Rủi Ro")

    chart_col, metric_col = st.columns([2, 1])

    with chart_col:
        chart_container()
        fig_dist = create_mc_distribution(
            pnl_final=result["pnl_final"],
            var_level=stats["var"],
            cvar_level=stats["cvar"],
            pnl_baseline=stats["pnl_baseline"],
            confidence_level=confidence_level,
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        chart_container_end()

    with metric_col:
        _render_risk_metrics(stats, conf_label)

    section_divider()

    # ── 4. Per-CW contribution (chỉ hiện khi danh mục > 1 CW) ─
    if per_cw and not is_single:
        section_title("▣", "Đóng Góp Kỳ Vọng Từng CW")
        chart_container()
        fig_contrib = create_mc_contribution(
            cw_names=[c["ma_cw"] for c in per_cw],
            expected_pnl=[c["expected_pnl"] for c in per_cw],
            std_pnl=[c["std_pnl"] for c in per_cw],
        )
        st.plotly_chart(fig_contrib, use_container_width=True)
        chart_container_end()

        _render_per_cw_table(per_cw)

    # ── Thông tin CW đơn lẻ chi tiết hơn ─────────────────────
    if is_single and per_cw:
        _render_single_cw_detail(per_cw[0], stats)


# ============================================================
# SUB-SECTIONS
# ============================================================

def _render_portfolio_table(result: dict, is_single: bool, sim_label: str):
    """Bảng tóm tắt CW tham gia simulation."""
    title = f"Thông Tin — {sim_label}" if is_single else "Danh Mục Tham Gia Simulation"
    section_title("≡", title)

    per_cw = result["per_cw"]
    if not per_cw:
        st.warning("Không có CW nào hợp lệ để hiển thị.")
        return

    rows = []
    for c in per_cw:
        current_pnl = (c["current_price"] - c["entry_price"]) * c["quantity"]
        rows.append({
            "Mã CW":        c["ma_cw"],
            "Cơ Sở":        c["ma_co_so"],
            "SL":           f"{c['quantity']:,}",
            "Giá Vào":      f"{c['entry_price']:,.0f}đ",
            "Giá Hiện Tại": f"{c['current_price']:,.0f}đ",
            "PnL Hiện Tại": f"{'+'if current_pnl>=0 else ''}{current_pnl:,.0f}đ",
        })

    df = pd.DataFrame(rows)
    table_container()
    render_table(df)
    table_container_end()

    n_paths = result["n_paths"]
    h_days = result["holding_days"]
    st.caption(
        f"Mô phỏng **{n_paths:,} paths** · Kỳ giữ **{h_days} ngày** · "
        f"**{len(per_cw)} CW** tham gia"
    )


def _render_risk_metrics(stats: dict, conf_label: str):
    """Hiển thị metrics rủi ro dạng cards."""
    mean_pnl = stats["mean"]
    var = stats["var"]
    cvar = stats["cvar"]
    prob_profit = stats["prob_profit"]
    baseline = stats["pnl_baseline"]

    # E[PnL]
    mean_color = "#2ECC71" if mean_pnl >= 0 else "#E74C3C"
    st.markdown(
        f'<div class="custom-metric-card">'
        f'<div class="custom-metric-label">E[PnL] Kỳ Vọng</div>'
        f'<div class="custom-metric-value" style="color:{mean_color};">'
        f'{"+" if mean_pnl >= 0 else ""}{mean_pnl:,.0f}đ</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Baseline
    base_color = "#2ECC71" if baseline >= 0 else "#E74C3C"
    st.markdown(
        f'<div class="custom-metric-card">'
        f'<div class="custom-metric-label">Baseline (Time Decay)</div>'
        f'<div class="custom-metric-value" style="color:{base_color};">'
        f'{"+" if baseline >= 0 else ""}{baseline:,.0f}đ</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # VaR
    st.markdown(
        f'<div class="custom-metric-card">'
        f'<div class="custom-metric-label">VaR {conf_label}</div>'
        f'<div class="custom-metric-value" style="color:#E74C3C;">'
        f'{var:,.0f}đ</div>'
        f'<div class="custom-metric-sublabel">Lỗ tối đa với xác suất {conf_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # CVaR
    st.markdown(
        f'<div class="custom-metric-card">'
        f'<div class="custom-metric-label">CVaR {conf_label} (Expected Shortfall)</div>'
        f'<div class="custom-metric-value" style="color:#FF4444;">'
        f'{cvar:,.0f}đ</div>'
        f'<div class="custom-metric-sublabel">PnL trung bình khi vượt VaR</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Prob profit
    prob_color = "#2ECC71" if prob_profit >= 0.5 else "#E74C3C"
    st.markdown(
        f'<div class="custom-metric-card">'
        f'<div class="custom-metric-label">Xác Suất Có Lãi</div>'
        f'<div class="custom-metric-value" style="color:{prob_color};">'
        f'{prob_profit*100:.1f}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Max gain / max loss
    st.markdown(
        f'<div class="custom-metric-card">'
        f'<div class="custom-metric-label">Max Gain (p99) / Max Loss (p1)</div>'
        f'<div class="custom-metric-value" style="font-size:0.95rem;">'
        f'<span style="color:#2ECC71;">+{stats["max_gain"]:,.0f}đ</span>'
        f' / '
        f'<span style="color:#E74C3C;">{stats["max_loss"]:,.0f}đ</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_single_cw_detail(cw_stats: dict, stats: dict):
    """Thông tin chi tiết thêm khi mô phỏng CW đơn lẻ."""
    section_title("◎", f"Chi Tiết — {cw_stats['ma_cw']}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        colored_metric(
            "E[PnL]",
            f"{'+'if cw_stats['expected_pnl']>=0 else ''}{cw_stats['expected_pnl']:,.0f}đ",
            "#2ECC71" if cw_stats['expected_pnl'] >= 0 else "#E74C3C",
        )
    with c2:
        colored_metric("Std PnL", f"±{cw_stats['std_pnl']:,.0f}đ", "#A78BFA")
    with c3:
        pp = cw_stats['prob_profit'] * 100
        colored_metric(
            "Xác Suất Lãi", f"{pp:.1f}%",
            "#2ECC71" if pp >= 50 else "#E74C3C",
        )
    with c4:
        colored_metric(
            "Median PnL",
            f"{'+'if stats['median']>=0 else ''}{stats['median']:,.0f}đ",
            "#2ECC71" if stats['median'] >= 0 else "#E74C3C",
        )


def _render_per_cw_table(per_cw: list[dict]):
    """Bảng chi tiết per-CW statistics."""
    rows = []
    for c in per_cw:
        rows.append({
            "Mã CW":          c["ma_cw"],
            "E[PnL]":         f"{'+'if c['expected_pnl']>=0 else ''}{c['expected_pnl']:,.0f}đ",
            "Std PnL":        f"±{c['std_pnl']:,.0f}đ",
            "Xác Suất Lãi":   f"{c['prob_profit']*100:.1f}%",
        })

    df = pd.DataFrame(rows)
    table_container()
    render_table(df)
    table_container_end()


# ============================================================
# HELPERS
# ============================================================

def _max_holding_days(portfolio: list[dict]) -> int:
    """Trả về số ngày tối đa có thể giữ (min của tất cả T còn lại)."""
    days_list = []
    for cw in portfolio:
        d = cw.get("days_remaining") or int(cw.get("T", 0.5) * 252)
        days_list.append(max(d, 1))
    if not days_list:
        return 30
    return min(min(days_list), 180)


def _cache_key(portfolio, n_paths, holding_days, confidence_level, mode) -> str:
    """Tạo hash key để cache kết quả simulation."""
    sig = f"{mode}|{n_paths}|{holding_days}|{confidence_level}"
    for cw in portfolio:
        sig += (
            f"|{cw.get('ma_cw')}:{cw.get('S')}:{cw.get('sigma')}"
            f":{cw.get('quantity')}:{cw.get('entry_price')}"
        )
    return hashlib.md5(sig.encode()).hexdigest()[:12]
