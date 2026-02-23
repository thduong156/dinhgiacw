"""
Tab Phòng Hộ Danh Mục — Kết hợp Cổ Phiếu + Chứng Quyền.

Hỗ trợ:
  - Nhập vị thế cổ phiếu (add/edit/delete)
  - 5 nhóm khẩu vị rủi ro
  - 3 chiến lược: Protective Put, Delta Hedging, Combined
"""

import streamlit as st
import pandas as pd
import numpy as np

from core.hedging import (
    RISK_PROFILES,
    StockPosition,
    calculate_net_greeks,
    protective_put_analysis,
    delta_hedge_recommendation,
    build_hedged_portfolio,
    generate_payoff_data,
)
from ui.components import (
    section_title,
    colored_metric,
    section_divider,
    chart_container,
    chart_container_end,
    table_container,
    table_container_end,
    tab_empty_state,
    format_vnd,
)
from ui.charts import (
    create_hedging_payoff_chart,
    create_delta_exposure_chart,
    create_risk_profile_radar,
)


# ── Helpers ──────────────────────────────────────────────────────

def _get_stock_positions() -> list[StockPosition]:
    """Lấy danh sách vị thế CP từ session_state."""
    raw = st.session_state.get("stock_positions", [])
    return [StockPosition(**sp) for sp in raw]


def _save_stock_positions(positions: list[StockPosition]):
    """Lưu danh sách vị thế CP vào session_state."""
    st.session_state["stock_positions"] = [
        {"ticker": sp.ticker, "entry_price": sp.entry_price,
         "quantity": sp.quantity, "current_price": sp.current_price}
        for sp in positions
    ]


def _get_underlyings_from_portfolio() -> dict:
    """Lấy dict {ticker_upper: current_price} từ CW portfolio."""
    portfolio = st.session_state.get("cw_portfolio", [])
    result = {}
    for cw in portfolio:
        tk = cw.get("ma_co_so", "").upper()
        if tk and cw.get("S", 0) > 0:
            result[tk] = cw["S"]
    return result


def _get_cw_portfolio() -> list[dict]:
    """Lấy CW portfolio từ session_state."""
    return st.session_state.get("cw_portfolio", [])


# ── Section 1: Vị Thế Cổ Phiếu ─────────────────────────────────

def _render_stock_positions():
    """Form nhập và quản lý vị thế cổ phiếu."""
    section_title("▪", "Vị Thế Cổ Phiếu")

    positions = _get_stock_positions()
    underlyings = _get_underlyings_from_portfolio()

    # Hiển thị vị thế hiện có
    if positions:
        st.markdown('<div class="stock-pos-grid">', unsafe_allow_html=True)
        cols = st.columns(min(len(positions), 4))
        for i, sp in enumerate(positions):
            with cols[i % len(cols)]:
                pnl = (sp.current_price - sp.entry_price) * sp.quantity
                pnl_pct = ((sp.current_price - sp.entry_price) / sp.entry_price * 100) if sp.entry_price > 0 else 0
                pnl_color = "#22C55E" if pnl >= 0 else "#EF4444"
                st.markdown(
                    f'<div class="stock-pos-card">'
                    f'<div class="stock-pos-ticker">{sp.ticker.upper()}</div>'
                    f'<div class="stock-pos-detail">'
                    f'Giá mua: {format_vnd(sp.entry_price)} | SL: {sp.quantity:,}</div>'
                    f'<div class="stock-pos-detail">'
                    f'Giá HT: {format_vnd(sp.current_price)} | '
                    f'GT: {format_vnd(sp.current_price * sp.quantity)}</div>'
                    f'<div class="stock-pos-pnl" style="color:{pnl_color}">'
                    f'PnL: {format_vnd(pnl)} ({pnl_pct:+.1f}%)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)

        # Delete buttons
        del_cols = st.columns(len(positions) + 1)
        for i, sp in enumerate(positions):
            with del_cols[i]:
                if st.button(f"× {sp.ticker.upper()}", key=f"del_sp_{i}"):
                    positions.pop(i)
                    _save_stock_positions(positions)
                    st.rerun()

    # Form thêm CP mới
    with st.expander("+ Thêm vị thế cổ phiếu", expanded=len(positions) == 0):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Suggest tickers from CW portfolio
            available_tickers = sorted(underlyings.keys())
            ticker = st.text_input(
                "Mã CP",
                placeholder="VD: MWG, VPB...",
                help=f"CP cùng mã cơ sở với CW: {', '.join(available_tickers)}" if available_tickers else "",
                key="hedging_ticker_input",
            ).strip().upper()
        with c2:
            auto_price = underlyings.get(ticker, 0)
            current_price = st.number_input(
                "Giá hiện tại",
                value=float(auto_price) if auto_price > 0 else 0.0,
                min_value=0.0,
                step=100.0,
                format="%.0f",
                key="hedging_current_price",
            )
        with c3:
            entry_price = st.number_input(
                "Giá mua",
                value=float(auto_price) if auto_price > 0 else 0.0,
                min_value=0.0,
                step=100.0,
                format="%.0f",
                key="hedging_entry_price",
            )
        with c4:
            quantity = st.number_input(
                "Số lượng",
                value=100,
                min_value=1,
                step=100,
                key="hedging_qty",
            )

        if st.button("+ Thêm cổ phiếu", key="add_stock_btn"):
            if ticker and current_price > 0 and entry_price > 0 and quantity > 0:
                positions.append(StockPosition(ticker, entry_price, quantity, current_price))
                _save_stock_positions(positions)
                st.rerun()
            else:
                st.warning("Vui lòng nhập đầy đủ thông tin cổ phiếu.")

    return positions


# ── Section 2: Chọn Khẩu Vị Rủi Ro ─────────────────────────────

def _render_risk_profile_selector() -> str:
    """5 buttons chọn risk profile. Returns profile key."""
    section_title("⊕", "Chọn Khẩu Vị Rủi Ro")

    if "hedging_profile" not in st.session_state:
        st.session_state["hedging_profile"] = "moderate"

    profile_keys = list(RISK_PROFILES.keys())
    cols = st.columns(5)

    for i, key in enumerate(profile_keys):
        p = RISK_PROFILES[key]
        is_selected = st.session_state["hedging_profile"] == key
        stock_lo, stock_hi = [int(x * 100) for x in p["target_stock_pct"]]
        cw_lo, cw_hi = [int(x * 100) for x in p["target_cw_pct"]]

        with cols[i]:
            border_color = "#FFFFFF" if is_selected else "#2E3348"
            bg = "#222633" if is_selected else "#1A1D27"
            shadow = "0 0 15px rgba(255,255,255,0.08)" if is_selected else "none"
            st.markdown(
                f'<div style="background:{bg};border:{"2px" if is_selected else "1px"} solid {border_color};'
                f'border-radius:12px;padding:14px 10px;text-align:center;box-shadow:{shadow};">'
                f'<div style="font-size:1.6rem;font-family:Fira Code,monospace;'
                f'font-weight:700;color:{p["color"]};margin-bottom:4px">{p["icon"]}</div>'
                f'<div style="font-family:Fira Code,monospace;'
                f'font-size:0.82rem;font-weight:600;color:#F0F4FF;margin-bottom:4px">{p["name_vi"]}</div>'
                f'<div style="font-size:0.7rem;color:#7A84A0;line-height:1.4;'
                f'margin-bottom:6px">{p["description"]}</div>'
                f'<div style="font-family:Fira Code,monospace;font-size:0.68rem;color:#B8C2DB;'
                f'padding:3px 6px;background:rgba(255,255,255,0.04);border-radius:4px;'
                f'display:inline-block">{stock_lo}-{stock_hi}% CP | {cw_lo}-{cw_hi}% CW</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                p["name_vi"],
                key=f"rp_btn_{key}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state["hedging_profile"] = key
                st.rerun()

    return st.session_state["hedging_profile"]


# ── Section 3: Tổng Quan Danh Mục ───────────────────────────────

def _render_portfolio_overview(stocks, cw_list, profile_key):
    """Hiển thị Net Greeks, tỷ trọng, so sánh target."""
    section_title("△", "Tổng Quan Danh Mục Phòng Hộ")

    profile = RISK_PROFILES[profile_key]
    greeks = calculate_net_greeks(stocks, cw_list)

    # Row 1: Value breakdown
    c1, c2, c3, c4, c5 = st.columns(5)

    total_val = greeks["total_value"]
    with c1:
        colored_metric("Tổng Giá Trị", f"{format_vnd(total_val)} đ", color="#F0F4FF")

    # Stock/CW ratio vs target
    stock_pct = greeks["stock_pct"]
    target_lo, target_hi = [x * 100 for x in profile["target_stock_pct"]]
    in_target = target_lo <= stock_pct <= target_hi
    ratio_color = "#22C55E" if in_target else "#F59E0B"
    with c2:
        colored_metric(
            f"CP / CW",
            f"{stock_pct:.0f}% / {greeks['cw_pct']:.0f}%",
            color=ratio_color,
            delta=f"Target: {target_lo:.0f}-{target_hi:.0f}%",
            delta_color=ratio_color,
        )

    # Net Delta vs target
    delta_lo, delta_hi = profile["target_net_delta"]
    net_d = greeks["net_delta"]
    in_delta = delta_lo <= net_d <= delta_hi if total_val > 0 else True
    delta_color = "#22C55E" if in_delta else "#EF4444"
    with c3:
        colored_metric(
            "Net Delta", f"{net_d:,.1f}",
            color=delta_color,
            delta=f"Target: {delta_lo:.1f} – {delta_hi:.1f}",
            delta_color=delta_color,
        )
    with c4:
        colored_metric("Net Gamma", f"{greeks['net_gamma']:,.4f}", color="#A78BFA")
    with c5:
        theta_val = greeks["net_theta"]
        theta_color = "#EF4444" if theta_val < 0 else "#22C55E"
        colored_metric("Net Theta", f"{format_vnd(theta_val)} /ngày", color=theta_color)

    return greeks


# ── Section 4: Chiến Lược Phòng Hộ ──────────────────────────────

def _render_strategies(stocks, cw_list, profile_key, greeks):
    """Render 3 chiến lược phòng hộ."""
    section_title("◇", "Chiến Lược Phòng Hộ")
    profile = RISK_PROFILES[profile_key]

    strat_tabs = st.tabs([
        "▪ Protective Put",
        "△ Delta Hedging",
        "◎ Combined Portfolio",
    ])

    # ── Strategy A: Protective Put ──
    with strat_tabs[0]:
        put_cw_list = [cw for cw in cw_list if cw.get("option_type") == "put"]

        if not stocks:
            st.info("Thêm vị thế cổ phiếu ở Section 1 để phân tích Protective Put.")
        elif not put_cw_list:
            st.info(
                "Không có CW Put trong danh mục. "
                "Thêm CW Put cùng mã cơ sở với cổ phiếu để sử dụng chiến lược Protective Put."
            )
        else:
            for sp in stocks:
                results = protective_put_analysis(sp, put_cw_list)
                if not results:
                    st.caption(f"Không có put CW cho {sp.ticker.upper()}")
                    continue

                st.markdown(
                    f'<div class="strategy-card">'
                    f'<div class="strategy-card-title">Protective Put — {sp.ticker.upper()}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                for r in results:
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    with mc1:
                        colored_metric("Put CW", r["ma_cw"].upper(), color="#93C5FD")
                    with mc2:
                        cost_color = "#22C55E" if r["cost_pct"] < 5 else "#F59E0B" if r["cost_pct"] < 10 else "#EF4444"
                        colored_metric("Chi Phí BV", f"{r['cost_pct']:.1f}%", color=cost_color)
                    with mc3:
                        colored_metric("Max Loss", f"{r['max_loss_pct']:.1f}%", color="#EF4444")
                    with mc4:
                        colored_metric("Break-Even", f"{format_vnd(r['break_even'])} đ", color="#F0F4FF")

                    # Payoff chart
                    if r.get("payoff_data"):
                        payoff = r["payoff_data"]
                        chart_data = {
                            "prices": payoff["prices"],
                            "stock_pnl": payoff["stock_pnl"],
                            "cw_pnl": payoff["put_pnl"],
                            "total_pnl": payoff["total_pnl"],
                            "break_evens": [],
                        }
                        chart_container("Payoff Diagram")
                        st.plotly_chart(
                            create_hedging_payoff_chart(chart_data),
                            use_container_width=True,
                            config={"displayModeBar": False},
                        )
                        chart_container_end()
                    section_divider()

    # ── Strategy B: Delta Hedging ──
    with strat_tabs[1]:
        target_lo, target_hi = profile["target_net_delta"]
        target_mid = (target_lo + target_hi) / 2

        st.markdown(
            f"**Target Net Delta:** {target_lo:.1f} – {target_hi:.1f} "
            f"(giữa = {target_mid:.1f})"
        )

        target_input = st.slider(
            "Target Delta",
            min_value=float(target_lo),
            max_value=float(target_hi),
            value=float(target_mid),
            step=0.1,
            key="hedge_target_delta",
        )

        rec = delta_hedge_recommendation(stocks, cw_list, target_input)

        # Delta gauge
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            d_color = "#22C55E" if abs(rec["delta_gap"]) < rec["rebalance_trigger"] else "#EF4444"
            colored_metric("Delta Hiện Tại", f"{rec['current_delta']:,.1f}", color=d_color)
        with mc2:
            colored_metric("Delta Mục Tiêu", f"{rec['target_delta']:.1f}", color="#F0F4FF")
        with mc3:
            gap_color = "#22C55E" if abs(rec["delta_gap"]) < 5 else "#F59E0B"
            colored_metric("Delta Gap", f"{rec['delta_gap']:+,.1f}", color=gap_color)

        # Recommendations
        if rec["recommendations"]:
            st.markdown('<div class="strategy-card">', unsafe_allow_html=True)
            st.markdown("**Đề xuất điều chỉnh:**")
            for r in rec["recommendations"]:
                st.markdown(f"- {r}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Delta exposure chart
        if rec["per_ticker"]:
            chart_container("Delta Exposure")
            st.plotly_chart(
                create_delta_exposure_chart(rec["per_ticker"], target_input),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            chart_container_end()

    # ── Strategy C: Combined Portfolio ──
    with strat_tabs[2]:
        result = build_hedged_portfolio(stocks, cw_list, profile_key)

        if result["recommendations"]:
            st.markdown('<div class="strategy-card">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="strategy-card-title">'
                f'Đề Xuất — {profile["name_vi"]}</div>',
                unsafe_allow_html=True,
            )
            for r in result["recommendations"]:
                st.markdown(f"- {r}")
            st.markdown('</div>', unsafe_allow_html=True)

        if result["excluded_cw"]:
            with st.expander(f"△ CW bị loại ({len(result['excluded_cw'])})"):
                for ec in result["excluded_cw"]:
                    st.caption(f"**{ec['cw'].get('ma_cw', '')}** — {ec['reason']}")

        # Payoff chart cho combined portfolio
        payoff = generate_payoff_data(stocks, cw_list)
        if payoff["prices"]:
            chart_container("Payoff Tổng Hợp")
            st.plotly_chart(
                create_hedging_payoff_chart(payoff),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            chart_container_end()


# ── Section 5: Bảng Phân Bổ Chi Tiết ────────────────────────────

def _render_allocation_table(stocks, cw_list, greeks):
    """Bảng tổng hợp tất cả vị thế CP + CW."""
    section_title("≡", "Bảng Phân Bổ Chi Tiết")

    rows = []
    total_val = greeks["total_value"]

    for sp in stocks:
        val = sp.current_price * sp.quantity
        weight = (val / total_val * 100) if total_val > 0 else 0
        pnl = (sp.current_price - sp.entry_price) * sp.quantity
        rows.append({
            "Loại": "CP",
            "Mã": sp.ticker.upper(),
            "Giá": format_vnd(sp.current_price),
            "SL": f"{sp.quantity:,}",
            "Giá Trị": format_vnd(val),
            "Tỷ Trọng": f"{weight:.1f}%",
            "Delta": f"{sp.quantity:,}",
            "PnL": format_vnd(pnl),
        })

    from core.hedging import _make_analyzer
    for cw in cw_list:
        qty = cw.get("quantity") or 0
        val = cw["cw_price"] * qty
        weight = (val / total_val * 100) if total_val > 0 else 0
        entry = cw.get("entry_price") or cw["cw_price"]
        pnl = (cw["cw_price"] - entry) * qty
        analyzer = _make_analyzer(cw)
        d = analyzer.greeks.delta() * qty
        rows.append({
            "Loại": f"CW ({cw.get('option_type', 'call')})",
            "Mã": cw.get("ma_cw", "").upper(),
            "Giá": format_vnd(cw["cw_price"]),
            "SL": f"{qty:,}",
            "Giá Trị": format_vnd(val),
            "Tỷ Trọng": f"{weight:.1f}%",
            "Delta": f"{d:,.2f}",
            "PnL": format_vnd(pnl),
        })

    if rows:
        table_container("Phân Bổ Danh Mục", badge=f"{len(rows)} vị thế")
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
        table_container_end()

        # CSV export
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "↓ Tải CSV",
            csv,
            file_name="hedging_portfolio.csv",
            mime="text/csv",
        )


# ── Section 6: Risk Profile Comparison ──────────────────────────

def _render_risk_comparison(profile_key):
    """Radar chart so sánh 5 nhóm rủi ro."""
    section_title("◎", "So Sánh Các Nhóm Khẩu Vị Rủi Ro")

    # Normalize values to 0-100 scale for radar
    profiles_data = []
    for key, p in RISK_PROFILES.items():
        delta_mid = sum(p["target_net_delta"]) / 2
        lev = p["max_leverage"]
        stock_mid = sum(p["target_stock_pct"]) / 2

        profiles_data.append({
            "name": p["name_vi"],
            "color": p["color"],
            "expected_return": min(100, delta_mid * 80 + 10),
            "risk": min(100, lev / 12 * 100),
            "net_delta_norm": min(100, delta_mid * 100),
            "leverage_norm": min(100, lev / 12 * 100),
            "protection_cost_norm": max(0, 100 - stock_mid * 100),
        })

    chart_container("Radar Chart")
    st.plotly_chart(
        create_risk_profile_radar(profiles_data),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    chart_container_end()


# ── Main Render ──────────────────────────────────────────────────

def render_hedging_tab():
    """Entry point cho tab Phòng Hộ Danh Mục."""
    cw_list = _get_cw_portfolio()

    if not cw_list:
        tab_empty_state(
            "⊘",
            "Chưa có chứng quyền trong danh mục",
            "Thêm CW ở sidebar để bắt đầu phân tích phòng hộ.",
            "Phòng hộ kết hợp CP + CW giúp kiểm soát rủi ro hiệu quả.",
        )
        return

    # Section 1: Vị thế CP
    stocks = _render_stock_positions()

    section_divider()

    # Section 2: Risk profile
    profile_key = _render_risk_profile_selector()

    section_divider()

    # Section 3: Portfolio overview
    greeks = _render_portfolio_overview(stocks, cw_list, profile_key)

    section_divider()

    # Section 4: Strategies
    _render_strategies(stocks, cw_list, profile_key, greeks)

    section_divider()

    # Section 5: Allocation table
    _render_allocation_table(stocks, cw_list, greeks)

    section_divider()

    # Section 6: Risk comparison
    _render_risk_comparison(profile_key)
