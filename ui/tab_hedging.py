"""
Tab Phòng Hộ Danh Mục — Kết hợp Cổ Phiếu + Chứng Quyền.

Lý thuyết nền tảng:
  - Hàm hữu dụng kỳ vọng: U = E[r] - (A/2)·σ²
  - A = hệ số ngại rủi ro (Risk Aversion Coefficient)
  - 3 loại nhà đầu tư dựa trên A: Thận Trọng (A=6), Cân Bằng (A=3), Tích Cực (A=1)
  - Danh mục tối ưu = argmax U trên Efficient Frontier
  - Đường đẳng hữu dụng (Indifference Curve): μ = (A/2)·σ² + U₀
"""

import streamlit as st
import pandas as pd
import numpy as np

from core.hedging import (
    StockPosition,
    calculate_net_greeks,
    protective_put_analysis,
    delta_hedge_recommendation,
    build_hedged_portfolio,
    generate_payoff_data,
)
from core.warrant import WarrantAnalyzer
from core.markowitz import (
    CWAsset,
    estimate_cw_return,
    estimate_cw_volatility,
    build_correlation_matrix,
    generate_efficient_frontier,
    find_optimal_for_investor,
    portfolio_metrics,
    build_covariance_matrix,
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
    render_table,
)
from ui.charts import (
    create_hedging_payoff_chart,
    create_delta_exposure_chart,
    create_efficient_frontier_chart,
)


# ── Định nghĩa 3 loại nhà đầu tư ────────────────────────────────

INVESTOR_TYPES = {
    "conservative": {
        "name_vi":    "Thận Trọng",
        "A":          6.0,
        "icon":       "◎",
        "color":      "#3B82F6",
        "description": "Ưu tiên bảo toàn vốn, chấp nhận lợi nhuận thấp để giảm rủi ro tối đa",
        "target":     "Gần Min-Variance",
        "bg":         "rgba(59,130,246,0.08)",
        "border":     "rgba(59,130,246,0.4)",
    },
    "balanced": {
        "name_vi":    "Cân Bằng",
        "A":          3.0,
        "icon":       "◈",
        "color":      "#F59E0B",
        "description": "Cân bằng giữa lợi nhuận và rủi ro, tối đa hoá tỷ lệ Sharpe",
        "target":     "Gần Max-Sharpe",
        "bg":         "rgba(245,158,11,0.08)",
        "border":     "rgba(245,158,11,0.4)",
    },
    "aggressive": {
        "name_vi":    "Tích Cực",
        "A":          1.0,
        "icon":       "△",
        "color":      "#EF4444",
        "description": "Chấp nhận rủi ro cao để tối đa hoá lợi nhuận kỳ vọng",
        "target":     "Gần Max-Return",
        "bg":         "rgba(239,68,68,0.08)",
        "border":     "rgba(239,68,68,0.4)",
    },
}

# Ánh xạ loại nhà đầu tư → tham số delta hedging tương đương
_INVESTOR_DELTA_TARGET = {
    "conservative": (0.3, 0.7),    # delta thấp → phòng thủ
    "balanced":     (0.5, 1.2),    # delta vừa
    "aggressive":   (0.8, 2.0),    # delta cao → đòn bẩy
}


# ── Helpers ──────────────────────────────────────────────────────

def _get_stock_positions() -> list[StockPosition]:
    raw = st.session_state.get("stock_positions", [])
    return [StockPosition(**sp) for sp in raw]


def _save_stock_positions(positions: list[StockPosition]):
    st.session_state["stock_positions"] = [
        {"ticker": sp.ticker, "entry_price": sp.entry_price,
         "quantity": sp.quantity, "current_price": sp.current_price}
        for sp in positions
    ]


def _get_underlyings_from_portfolio() -> dict:
    portfolio = st.session_state.get("cw_portfolio", [])
    result = {}
    for cw in portfolio:
        tk = cw.get("ma_co_so", "").upper()
        if tk and cw.get("S", 0) > 0:
            result[tk] = cw["S"]
    return result


def _get_cw_portfolio() -> list[dict]:
    return st.session_state.get("cw_portfolio", [])


def _build_cw_assets(cw_list: list[dict]) -> list[CWAsset]:
    """
    Chuyển danh mục CW → list[CWAsset] để tính Efficient Frontier.
    Dùng WarrantAnalyzer.full_analysis() + estimate_cw_return/volatility.
    """
    assets = []
    for cw in cw_list:
        if not cw.get("cw_price") or cw["cw_price"] <= 0:
            continue
        if not cw.get("T") or cw["T"] <= 0:
            continue
        try:
            analyzer = WarrantAnalyzer(
                S=cw["S"], K=cw["K"], T=cw["T"],
                r=cw["r"], sigma=cw["sigma"],
                cw_market_price=cw["cw_price"],
                conversion_ratio=cw["cr"],
                option_type=cw["option_type"],
                q=cw.get("q", 0.0),
            )
            analysis = analyzer.full_analysis()
            cw_input = {
                "T":              cw["T"],
                "sigma":          cw["sigma"],
                "option_type":    cw["option_type"],
                "cw_price":       cw["cw_price"],
                "ma_co_so":       cw.get("ma_co_so", "N/A"),
                "days_remaining": max(int(cw["T"] * 365), 1),
            }
            exp_ret = estimate_cw_return(analysis, cw_input)
            vol     = estimate_cw_volatility(analysis, cw_input)
            assets.append(CWAsset(
                name=cw.get("ma_cw", f"CW{len(assets)+1}"),
                expected_return=exp_ret,
                volatility=vol,
                cw_price=cw["cw_price"],
                ma_co_so=cw.get("ma_co_so", "N/A"),
                option_type=cw["option_type"],
                score=cw.get("score", 50),
            ))
        except Exception:
            continue
    return assets


# ── Section 1: Vị Thế Cổ Phiếu ─────────────────────────────────

def _render_stock_positions():
    section_title("▪", "Vị Thế Cổ Phiếu")

    positions  = _get_stock_positions()
    underlyings = _get_underlyings_from_portfolio()

    if positions:
        cols = st.columns(min(len(positions), 4))
        for i, sp in enumerate(positions):
            with cols[i % len(cols)]:
                pnl     = (sp.current_price - sp.entry_price) * sp.quantity
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

        del_cols = st.columns(len(positions) + 1)
        for i, sp in enumerate(positions):
            with del_cols[i]:
                if st.button(f"× {sp.ticker.upper()}", key=f"del_sp_{i}"):
                    positions.pop(i)
                    _save_stock_positions(positions)
                    st.rerun()

    with st.expander("+ Thêm vị thế cổ phiếu", expanded=len(positions) == 0):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            available = sorted(underlyings.keys())
            ticker = st.text_input(
                "Mã CP",
                placeholder="VD: MWG, VPB...",
                help=f"CP cùng mã cơ sở với CW: {', '.join(available)}" if available else "",
                key="hedging_ticker_input",
            ).strip().upper()
        with c2:
            auto_price = underlyings.get(ticker, 0)
            current_price = st.number_input(
                "Giá hiện tại", value=float(auto_price) if auto_price > 0 else 0.0,
                min_value=0.0, step=100.0, format="%.0f", key="hedging_current_price",
            )
        with c3:
            entry_price = st.number_input(
                "Giá mua", value=float(auto_price) if auto_price > 0 else 0.0,
                min_value=0.0, step=100.0, format="%.0f", key="hedging_entry_price",
            )
        with c4:
            quantity = st.number_input(
                "Số lượng", value=100, min_value=1, step=100, key="hedging_qty",
            )

        if st.button("+ Thêm cổ phiếu", key="add_stock_btn"):
            if ticker and current_price > 0 and entry_price > 0 and quantity > 0:
                positions.append(StockPosition(ticker, entry_price, quantity, current_price))
                _save_stock_positions(positions)
                st.rerun()
            else:
                st.warning("Vui lòng nhập đầy đủ thông tin cổ phiếu.")

    return positions


# ── Section 2: Chọn Loại Nhà Đầu Tư ─────────────────────────────

def _render_investor_selector() -> str:
    """3 card button chọn loại nhà đầu tư theo hàm hữu dụng. Returns key."""
    section_title("⊕", "Loại Nhà Đầu Tư — Hàm Hữu Dụng U = E[r] − (A/2)·σ²")

    if "hedging_investor_type" not in st.session_state:
        st.session_state["hedging_investor_type"] = "balanced"

    st.markdown(
        '<div class="info-box">'
        '<b>Hàm hữu dụng kỳ vọng:</b> U = E[r] − (A/2)·σ²<br>'
        '&bull; <b>A</b> = hệ số ngại rủi ro (Risk Aversion Coefficient)<br>'
        '&bull; A lớn → ngại rủi ro cao → chọn danh mục σ thấp<br>'
        '&bull; A nhỏ → ưa rủi ro → chọn danh mục E[r] cao<br>'
        '&bull; Danh mục tối ưu = điểm trên Efficient Frontier tiếp xúc đường đẳng hữu dụng'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for i, (key, inv) in enumerate(INVESTOR_TYPES.items()):
        is_sel = st.session_state["hedging_investor_type"] == key
        border_w = "2px" if is_sel else "1px"
        bg       = inv["bg"] if is_sel else "#1A1D27"
        shadow   = f"0 0 18px {inv['border']}" if is_sel else "none"

        with cols[i]:
            st.markdown(
                f'<div style="background:{bg};border:{border_w} solid {inv["border"]};'
                f'border-radius:14px;padding:16px 12px;text-align:center;'
                f'box-shadow:{shadow};margin-bottom:4px;">'
                f'<div style="font-size:1.8rem;color:{inv["color"]};margin-bottom:6px;">'
                f'{inv["icon"]}</div>'
                f'<div style="font-size:0.9rem;font-weight:700;color:#F0F4FF;margin-bottom:4px;">'
                f'{inv["name_vi"]}</div>'
                f'<div style="font-family:Fira Code,monospace;font-size:1.1rem;'
                f'font-weight:800;color:{inv["color"]};margin-bottom:6px;">A = {inv["A"]:.0f}</div>'
                f'<div style="font-size:0.7rem;color:#8896AB;line-height:1.5;margin-bottom:8px;">'
                f'{inv["description"]}</div>'
                f'<div style="font-size:0.68rem;color:{inv["color"]};'
                f'background:rgba(255,255,255,0.05);border-radius:6px;padding:3px 8px;'
                f'display:inline-block;">{inv["target"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                f'{"✓ " if is_sel else ""}{inv["name_vi"]}',
                key=f"inv_btn_{key}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state["hedging_investor_type"] = key
                st.rerun()

    return st.session_state["hedging_investor_type"]


# ── Section 3: Đường Cong Hiệu Quả ──────────────────────────────

def _render_efficient_frontier(cw_list: list[dict], investor_key: str):
    """Tính toán và vẽ Efficient Frontier + điểm tối ưu 3 loại nhà đầu tư."""
    section_title("◇", "Đường Cong Hiệu Quả Markowitz")

    assets = _build_cw_assets(cw_list)

    if len(assets) < 2:
        st.markdown(
            '<div class="info-box" style="border-color:rgba(245,158,11,0.4);">'
            '⚠ Cần ít nhất <b>2 CW</b> trong danh mục để tính Efficient Frontier.<br>'
            'Thêm CW vào danh mục ở sidebar để bật tính năng này.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Đang tính Efficient Frontier..."):
        corr     = build_correlation_matrix(assets)
        cov      = build_covariance_matrix(assets, corr)
        frontier = generate_efficient_frontier(assets, corr, n_portfolios=6000)

        # Tính danh mục tối ưu cho 3 loại nhà đầu tư
        investor_points = []
        for key, inv in INVESTOR_TYPES.items():
            opt = find_optimal_for_investor(frontier, inv["A"])
            investor_points.append({
                "key":         key,
                "name_vi":     inv["name_vi"],
                "A":           inv["A"],
                "color":       inv["color"],
                "port_return": opt["port_return"],
                "port_vol":    opt["port_vol"],
                "utility":     opt["utility"],
                "sharpe":      opt["sharpe"],
                "weights":     opt["weights"],
            })

    # ── Hiển thị 3 metrics tóm tắt ──
    sel_ip = next(ip for ip in investor_points if ip["key"] == investor_key)
    inv    = INVESTOR_TYPES[investor_key]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        colored_metric(
            f"Nhà đầu tư {inv['name_vi']}",
            f"A = {inv['A']:.0f}",
            color=inv["color"],
            delta="Hệ số ngại rủi ro",
        )
    with m2:
        colored_metric(
            "E[r] Tối Ưu",
            f"{sel_ip['port_return']*100:+.2f}%",
            color="#22C55E" if sel_ip["port_return"] > 0 else "#EF4444",
        )
    with m3:
        colored_metric(
            "σ Danh Mục",
            f"{sel_ip['port_vol']*100:.2f}%",
            color=inv["color"],
        )
    with m4:
        colored_metric(
            "Hữu Dụng U",
            f"{sel_ip['utility']:.4f}",
            color=inv["color"],
            delta=f"Sharpe = {sel_ip['sharpe']:.3f}",
        )

    # ── Chart ──
    chart_container("Efficient Frontier — Không gian (σ, E[r])")
    fig = create_efficient_frontier_chart(frontier, investor_points, assets, investor_key)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    chart_container_end()

    # ── Bảng trọng số tối ưu cho loại đang chọn ──
    section_title("≡", f"Trọng Số Tối Ưu — {inv['name_vi']} (A = {inv['A']:.0f})")

    st.markdown(
        f'<div class="info-box" style="border-color:{inv["border"]};">'
        f'Công thức: <b>U = E[r] − ({inv["A"]:.0f}/2)·σ² = E[r] − {inv["A"]/2:.1f}·σ²</b><br>'
        f'Danh mục tối ưu: E[r] = {sel_ip["port_return"]*100:+.2f}%  |  '
        f'σ = {sel_ip["port_vol"]*100:.2f}%  |  '
        f'U* = {sel_ip["utility"]:.4f}  |  '
        f'Sharpe = {sel_ip["sharpe"]:.3f}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Cards trọng số
    n = len(assets)
    weight_cols = st.columns(min(n, 4))
    for i, asset in enumerate(assets):
        w = sel_ip["weights"][i]
        w_color = inv["color"] if w > 0.15 else "#94A3B8"
        with weight_cols[i % min(n, 4)]:
            colored_metric(
                asset.name,
                f"{w*100:.1f}%",
                color=w_color,
                delta=f"E[r]={asset.expected_return*100:+.1f}% | σ={asset.volatility*100:.1f}%",
                delta_color="#8896AB",
            )

    # Bảng so sánh 3 loại
    compare_rows = []
    for ip in investor_points:
        compare_rows.append({
            "Loại NĐT": f"{INVESTOR_TYPES[ip['key']]['icon']} {ip['name_vi']}",
            "Hệ số A": f"{ip['A']:.0f}",
            "E[r] (%)": f"{ip['port_return']*100:+.2f}%",
            "σ (%)": f"{ip['port_vol']*100:.2f}%",
            "Hữu Dụng U": f"{ip['utility']:.4f}",
            "Sharpe": f"{ip['sharpe']:.3f}",
        })

    table_container("So Sánh Danh Mục Tối Ưu — 3 Loại Nhà Đầu Tư", badge="3 loại")
    render_table(pd.DataFrame(compare_rows))
    table_container_end()

    return investor_points, sel_ip


# ── Section 4: Tổng Quan Danh Mục ───────────────────────────────

def _render_portfolio_overview(stocks, cw_list, investor_key):
    section_title("△", "Tổng Quan Danh Mục Phòng Hộ")

    inv    = INVESTOR_TYPES[investor_key]
    greeks = calculate_net_greeks(stocks, cw_list)

    lo_ratio, hi_ratio = _INVESTOR_DELTA_TARGET[investor_key]
    total_val  = greeks["total_value"]
    stock_pct  = greeks["stock_pct"]
    net_d      = greeks["net_delta"]

    # Tính target delta tuyệt đối
    stock_delta  = float(sum(sp.current_price and sp.quantity or 0 for sp in stocks))
    base_delta   = max(sum(sp.quantity for sp in stocks) if stocks else 0,
                       abs(net_d), 1.0)
    delta_lo_abs = base_delta * lo_ratio
    delta_hi_abs = base_delta * hi_ratio

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        colored_metric("Tổng Giá Trị", f"{format_vnd(total_val)} đ", color="#F0F4FF")
    with c2:
        colored_metric(
            "CP / CW",
            f"{stock_pct:.0f}% / {greeks['cw_pct']:.0f}%",
            color=inv["color"],
            delta=f"Loại: {inv['name_vi']}",
            delta_color=inv["color"],
        )
    with c3:
        in_delta = delta_lo_abs <= net_d <= delta_hi_abs if total_val > 0 else True
        d_color  = "#22C55E" if in_delta else "#EF4444"
        colored_metric(
            "Net Delta", f"{net_d:,.1f}",
            color=d_color,
            delta=f"Target: {delta_lo_abs:,.0f} – {delta_hi_abs:,.0f}",
            delta_color=d_color,
        )
    with c4:
        colored_metric("Net Gamma", f"{greeks['net_gamma']:,.4f}", color="#A78BFA")
    with c5:
        theta_val   = greeks["net_theta"]
        theta_color = "#EF4444" if theta_val < 0 else "#22C55E"
        colored_metric("Net Theta", f"{format_vnd(theta_val)} /ngày", color=theta_color)

    return greeks


# ── Section 5: Chiến Lược Phòng Hộ ──────────────────────────────

def _render_strategies(stocks, cw_list, investor_key, greeks):
    section_title("◇", "Chiến Lược Phòng Hộ")

    strat_tabs = st.tabs([
        "▪ Mua Bảo Hiểm Put",
        "△ Cân Bằng Delta",
        "◎ Danh Mục Kết Hợp",
    ])

    # ── A: Protective Put ──
    with strat_tabs[0]:
        put_cw_list = [cw for cw in cw_list if cw.get("option_type") == "put"]

        if not stocks:
            st.info("Thêm vị thế cổ phiếu ở Section 1 để phân tích Protective Put.")
        elif not put_cw_list:
            st.info(
                "Không có CW Put trong danh mục. "
                "Thêm CW Put cùng mã cơ sở với cổ phiếu để sử dụng chiến lược này."
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

                    if r.get("payoff_data"):
                        pd_data = r["payoff_data"]
                        chart_data = {
                            "prices":     pd_data["prices"],
                            "stock_pnl":  pd_data["stock_pnl"],
                            "cw_pnl":     pd_data["put_pnl"],
                            "total_pnl":  pd_data["total_pnl"],
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

    # ── B: Cân Bằng Delta ──
    with strat_tabs[1]:
        inv = INVESTOR_TYPES[investor_key]

        # Tính base delta từ cổ phiếu (1 delta/cổ phiếu) + delta CW hiện tại
        stock_delta = float(sum(sp.quantity for sp in stocks)) if stocks else 0.0
        current_net = float(greeks["net_delta"])
        # Base = lấy delta cổ phiếu làm gốc; nếu không có CP dùng net delta
        base_delta = max(stock_delta, abs(current_net), 1.0)

        # Chuyển ratio → giá trị tuyệt đối
        lo_ratio, hi_ratio = _INVESTOR_DELTA_TARGET[investor_key]
        delta_lo_abs = base_delta * lo_ratio
        delta_hi_abs = base_delta * hi_ratio
        target_mid   = (delta_lo_abs + delta_hi_abs) / 2.0

        # Tính step gọn: ~1/50 của range
        raw_step = (delta_hi_abs - delta_lo_abs) / 50.0
        if   raw_step >= 10000: step_val = round(raw_step / 10000) * 10000
        elif raw_step >= 1000:  step_val = round(raw_step / 1000)  * 1000
        elif raw_step >= 100:   step_val = round(raw_step / 100)   * 100
        elif raw_step >= 10:    step_val = round(raw_step / 10)    * 10
        elif raw_step >= 1:     step_val = max(round(raw_step), 1)
        else:                   step_val = 1.0

        st.markdown(
            f'<div class="info-box" style="border-color:{inv["border"]};">'
            f'Target Net Delta cho <b>{inv["name_vi"]}</b> (A={inv["A"]:.0f}): '
            f'<b>{delta_lo_abs:,.0f} – {delta_hi_abs:,.0f}</b>'
            f'&nbsp;<span style="color:#8896AB;font-size:0.8em;">'
            f'({lo_ratio*100:.0f}–{hi_ratio*100:.0f}% delta cổ phiếu)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Reset slider khi investor_key thay đổi
        prev_key = st.session_state.get("_hedge_delta_prev_key")
        if prev_key != investor_key:
            st.session_state["hedge_target_delta"] = float(target_mid)
            st.session_state["_hedge_delta_prev_key"] = investor_key

        target_input = st.slider(
            "Target Delta",
            min_value=float(delta_lo_abs),
            max_value=float(delta_hi_abs),
            value=float(st.session_state.get("hedge_target_delta", target_mid)),
            step=float(step_val),
            key="hedge_target_delta",
        )

        rec = delta_hedge_recommendation(stocks, cw_list, target_input)

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            d_color = "#22C55E" if abs(rec["delta_gap"]) < rec["rebalance_trigger"] else "#EF4444"
            colored_metric("Delta Hiện Tại", f"{rec['current_delta']:,.1f}", color=d_color)
        with mc2:
            colored_metric("Delta Mục Tiêu", f"{rec['target_delta']:.2f}", color="#F0F4FF")
        with mc3:
            gap_color = "#22C55E" if abs(rec["delta_gap"]) < 5 else "#F59E0B"
            colored_metric("Delta Gap", f"{rec['delta_gap']:+,.1f}", color=gap_color)

        if rec["recommendations"]:
            st.markdown('<div class="strategy-card">', unsafe_allow_html=True)
            st.markdown("**Đề xuất điều chỉnh:**")
            for r in rec["recommendations"]:
                st.markdown(f"- {r}")
            st.markdown('</div>', unsafe_allow_html=True)

        if rec["per_ticker"]:
            chart_container("Delta Exposure")
            st.plotly_chart(
                create_delta_exposure_chart(rec["per_ticker"], target_input),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            chart_container_end()

    # ── C: Combined Portfolio ──
    with strat_tabs[2]:
        # Dùng profile_key tương ứng với investor_key cho build_hedged_portfolio
        _profile_map = {
            "conservative": "conservative",
            "balanced":     "moderate",
            "aggressive":   "aggressive",
        }
        profile_key = _profile_map.get(investor_key, "moderate")
        result = build_hedged_portfolio(stocks, cw_list, profile_key)

        if result["recommendations"]:
            inv = INVESTOR_TYPES[investor_key]
            st.markdown(
                f'<div class="strategy-card">'
                f'<div class="strategy-card-title">'
                f'Đề Xuất — {inv["name_vi"]} (A = {inv["A"]:.0f})</div>',
                unsafe_allow_html=True,
            )
            for r in result["recommendations"]:
                st.markdown(f"- {r}")
            st.markdown('</div>', unsafe_allow_html=True)

        if result["excluded_cw"]:
            with st.expander(f"△ CW bị loại ({len(result['excluded_cw'])})"):
                for ec in result["excluded_cw"]:
                    st.caption(f"**{ec['cw'].get('ma_cw', '')}** — {ec['reason']}")

        payoff = generate_payoff_data(stocks, cw_list)
        if payoff["prices"]:
            chart_container("Payoff Tổng Hợp")
            st.plotly_chart(
                create_hedging_payoff_chart(payoff),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            chart_container_end()


# ── Section 6: Bảng Phân Bổ Chi Tiết ────────────────────────────

def _render_allocation_table(stocks, cw_list, greeks):
    section_title("≡", "Bảng Phân Bổ Chi Tiết")

    rows      = []
    total_val = greeks["total_value"]

    for sp in stocks:
        val    = sp.current_price * sp.quantity
        weight = (val / total_val * 100) if total_val > 0 else 0
        pnl    = (sp.current_price - sp.entry_price) * sp.quantity
        rows.append({
            "Loại": "CP",
            "Mã":        sp.ticker.upper(),
            "Giá":       format_vnd(sp.current_price),
            "SL":        f"{sp.quantity:,}",
            "Giá Trị":   format_vnd(val),
            "Tỷ Trọng":  f"{weight:.1f}%",
            "Delta":     f"{sp.quantity:,}",
            "PnL":       format_vnd(pnl),
        })

    from core.hedging import _make_analyzer
    for cw in cw_list:
        qty    = cw.get("quantity") or 0
        val    = cw["cw_price"] * qty
        weight = (val / total_val * 100) if total_val > 0 else 0
        entry  = cw.get("entry_price") or cw["cw_price"]
        pnl    = (cw["cw_price"] - entry) * qty
        az     = _make_analyzer(cw)
        d      = az.greeks.delta() * qty
        rows.append({
            "Loại":      f"CW ({cw.get('option_type', 'call')})",
            "Mã":        cw.get("ma_cw", "").upper(),
            "Giá":       format_vnd(cw["cw_price"]),
            "SL":        f"{qty:,}",
            "Giá Trị":   format_vnd(val),
            "Tỷ Trọng":  f"{weight:.1f}%",
            "Delta":     f"{d:,.2f}",
            "PnL":       format_vnd(pnl),
        })

    if rows:
        table_container("Phân Bổ Danh Mục", badge=f"{len(rows)} vị thế")
        render_table(pd.DataFrame(rows))
        table_container_end()

        df  = pd.DataFrame(rows)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "↓ Tải CSV", csv,
            file_name="hedging_portfolio.csv",
            mime="text/csv",
        )


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

    # Section 2: Chọn loại nhà đầu tư
    investor_key = _render_investor_selector()

    section_divider()

    # Section 3: Đường cong hiệu quả
    _render_efficient_frontier(cw_list, investor_key)

    section_divider()

    # Section 4: Tổng quan danh mục
    greeks = _render_portfolio_overview(stocks, cw_list, investor_key)

    section_divider()

    # Section 5: Chiến lược phòng hộ
    _render_strategies(stocks, cw_list, investor_key, greeks)

    section_divider()

    # Section 6: Bảng phân bổ
    _render_allocation_table(stocks, cw_list, greeks)
