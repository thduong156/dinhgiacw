import streamlit as st
from datetime import date, timedelta


def render_header():
    """Hiển thị header chính của ứng dụng."""
    st.markdown(
        '<div class="app-header">'
        '<div class="app-header-badge">Black-Scholes Model</div>'
        '<div class="main-header">PHÂN TÍCH CHỨNG QUYỀN</div>'
        '<div class="sub-header">Covered Warrant Analysis Tool &bull; Mô Hình Black-Scholes</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def section_title(icon: str, text: str):
    """Render tiêu đề section với icon."""
    st.markdown(
        f'<div class="section-title">'
        f'<div class="section-title-icon">{icon}</div>'
        f'<div class="section-title-text">{text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _clear_money_cache(prefix: str):
    """Xoá cache _money_input khi đóng/mở form edit để tránh dữ liệu cũ."""
    suffixes = ["_S", "_K", "_cw_price", "_entry_price", "_quantity"]
    for suffix in suffixes:
        st.session_state.pop(f"_money_{prefix}{suffix}", None)
        st.session_state.pop(f"{prefix}{suffix}", None)


def _money_input(label, default, min_val, max_val, step, key, help_text=""):
    """
    Number input hiển thị dấu phẩy ngay trong ô nhập.
    Dùng session_state để lưu giá trị số, hiển thị formatted.
    """
    state_key = f"_money_{key}"

    # Khởi tạo lần đầu
    if state_key not in st.session_state:
        st.session_state[state_key] = float(default)

    current_val = st.session_state[state_key]
    display_val = f"{current_val:,.0f}"

    raw = st.text_input(
        label,
        value=display_val,
        key=key,
        help=help_text,
    )

    # Parse: bỏ dấu phẩy, dấu cách, ký tự đ
    cleaned = raw.replace(",", "").replace(".", "").replace(" ", "").replace("đ", "").strip()

    try:
        parsed = float(cleaned)
        parsed = max(min_val, min(max_val, parsed))
    except (ValueError, TypeError):
        parsed = current_val  # Giữ nguyên nếu nhập sai

    st.session_state[state_key] = parsed
    return parsed


# ============================================================
# SIDEBAR — PROFESSIONAL VERSION
# ============================================================

def parameter_sidebar():
    """
    Sidebar — 3 sections:
    1. Chọn CW Phân Tích (selectbox + mini-dashboard → Tab 1-5)
    2. Portfolio (cards + add/CSV)
    3. Lưu / Tải Portfolio (JSON)
    Returns selected cw_entry dict, or None if portfolio is empty.
    """
    with st.sidebar:
        # Branded header
        _render_sidebar_brand()

        # === Khởi tạo cw_portfolio TRƯỚC KHI render bất kỳ section nào ===
        if "cw_portfolio" not in st.session_state:
            st.session_state["cw_portfolio"] = []
        loaded = st.session_state.pop("_loaded_portfolio_cw", None)
        if loaded:
            st.session_state["cw_portfolio"] = loaded

        # ============ SECTION 1: CHỌN CW PHÂN TÍCH ============
        _render_section_header("CHỌN CW PHÂN TÍCH")

        portfolio = st.session_state.get("cw_portfolio", [])
        selected_cw = None

        if portfolio:
            selected_cw = _render_cw_selector(portfolio)
            _render_selected_dashboard(selected_cw)
        else:
            _render_empty_state(
                "◈",
                "Chưa có CW nào",
                "Thêm CW ở phần Portfolio bên dưới để bắt đầu phân tích.",
            )

        # ============ SECTION 2: PORTFOLIO ============
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        _render_section_header("PORTFOLIO")
        _render_portfolio_section()

        # ============ SECTION 3: LƯU / TẢI ============
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        _render_section_header("LƯU / TẢI")
        _render_save_load_section()

    return selected_cw


# ============================================================
# SIDEBAR BRAND & SECTION HEADERS
# ============================================================

def _render_sidebar_brand():
    """Render branded header cho sidebar."""
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-brand-icon">◈</div>'
        '<div class="sb-brand-title">CW Analyzer</div>'
        '<div class="sb-brand-subtitle">Covered Warrant Dashboard</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_section_header(text: str):
    """Render section header: dot + label + fading line."""
    st.markdown(
        f'<div class="sb-section">'
        f'<div class="sb-section-dot"></div>'
        f'<span class="sb-section-label">{text}</span>'
        f'<div class="sb-section-line"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_empty_state(icon: str, title: str, text: str):
    """Render empty state placeholder."""
    st.markdown(
        f'<div class="sb-empty-state">'
        f'<div class="sb-empty-state-icon">{icon}</div>'
        f'<div class="sb-empty-state-title">{title}</div>'
        f'<div class="sb-empty-state-text">{text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SECTION 1: CW SELECTOR + MINI-DASHBOARD
# ============================================================

def _render_cw_selector(portfolio: list) -> dict:
    """Render CW selector với styled wrapper và collapsed label."""
    # Build display labels
    cw_labels = []
    for idx, cw in enumerate(portfolio):
        loai = "CALL" if cw["option_type"] == "call" else "PUT"
        ma = cw.get("ma_cw", f"CW #{idx}")
        cs = cw.get("ma_co_so", "?")
        cw_labels.append(f"{ma}  |  {loai}  |  {cs}")

    # Styled label with pulse dot
    st.markdown(
        '<div class="sb-selector-wrapper">'
        '<div class="sb-selector-label">'
        '<span class="pulse-dot"></span>'
        'CW đang phân tích'
        '</div>',
        unsafe_allow_html=True,
    )

    # Clamp index nếu portfolio bị thu nhỏ
    stored_idx = st.session_state.get("selected_cw_index", 0)
    if stored_idx >= len(portfolio):
        st.session_state["selected_cw_index"] = max(0, len(portfolio) - 1)

    selected_idx = st.selectbox(
        "Chọn CW",
        options=range(len(portfolio)),
        format_func=lambda i: cw_labels[i],
        key="selected_cw_index",
        label_visibility="collapsed",
    )

    # Close wrapper
    st.markdown('</div>', unsafe_allow_html=True)

    return portfolio[selected_idx]


def _render_position_pnl_html(cw: dict) -> str:
    """Generate HTML for position P&L display in mini-dashboard."""
    entry_p = cw.get("entry_price")
    qty = cw.get("quantity")
    if not entry_p or not qty or entry_p <= 0 or qty <= 0:
        return ""

    cw_price = cw["cw_price"]
    pnl_vnd = (cw_price - entry_p) * qty
    pnl_pct = ((cw_price / entry_p) - 1) * 100 if entry_p > 0 else 0
    cost = entry_p * qty
    market_val = cw_price * qty

    if pnl_vnd >= 0:
        pnl_color = "#22C55E"
        pnl_sign = "+"
        pnl_icon = "△"
    else:
        pnl_color = "#EF4444"
        pnl_sign = ""
        pnl_icon = "▽"

    return (
        f'<div style="margin-top:8px; padding:8px 10px; '
        f'background:rgba(255,255,255,0.03); border-radius:10px; '
        f'border:1px solid rgba(255,255,255,0.06);">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f'margin-bottom:4px;">'
        f'<span style="font-size:0.65rem; color:#64748B; text-transform:uppercase; '
        f'letter-spacing:0.5px;">Vị thế {pnl_icon}</span>'
        f'<span style="font-size:0.78rem; font-weight:800; color:{pnl_color}; '
        f"font-family:'Fira Code',monospace;\">{pnl_sign}{format_vnd(pnl_vnd)}đ</span>"
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:0.65rem; '
        f'color:#94A3B8;">'
        f'<span>SL: {qty:,} · Giá vào: {format_vnd(entry_p)}</span>'
        f'<span style="color:{pnl_color};">{pnl_sign}{pnl_pct:.1f}%</span>'
        f'</div>'
        f'</div>'
    )


def _render_selected_dashboard(cw: dict):
    """Render mini-dashboard cho CW đang chọn — visual rich thay cho summary table cũ."""
    S = cw["S"]
    K = cw["K"]
    option_type_val = cw["option_type"]
    days = cw.get("days_remaining", 0)
    cr = cw["cr"]
    cw_price = cw["cw_price"]

    # Moneyness
    if option_type_val == "call":
        moneyness = "itm" if S > K else ("otm" if S < K else "atm")
    else:
        moneyness = "itm" if S < K else ("otm" if S > K else "atm")

    moneyness_text = {"itm": "ITM", "otm": "OTM", "atm": "ATM"}[moneyness]
    type_class = "call" if option_type_val == "call" else "put"
    type_text = "CALL" if option_type_val == "call" else "PUT"

    # S/K ratio
    sk_ratio = f"{S/K:.3f}" if K > 0 else "N/A"

    # Time bar
    max_days = 365
    time_pct = min(100, (days / max_days) * 100) if max_days > 0 else 0
    if days > 90:
        time_color = "#22C55E"
    elif days > 30:
        time_color = "#F59E0B"
    else:
        time_color = "#EF4444"

    # Build position P&L HTML if applicable
    position_html = _render_position_pnl_html(cw)

    dash_html = (
        f'<div class="sb-dash">'
        f'<div class="sb-dash-header">'
        f'<span class="sb-dash-cw-name">{cw.get("ma_cw", "N/A").upper()}</span>'
        f'<span class="sb-dash-type-badge {type_class}">{type_text}</span>'
        f'</div>'
        f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">'
        f'<span style="font-size:0.72rem; color:#64748B;">'
        f'Cơ sở: <b style="color:#CBD5E0;">{cw.get("ma_co_so", "N/A").upper()}</b>'
        f'</span>'
        f'<span class="sb-moneyness {moneyness}">{moneyness_text}</span>'
        f'</div>'
        f'<div class="sb-metrics-grid">'
        f'<div class="sb-metric-mini">'
        f'<div class="sb-metric-mini-label">Giá CS</div>'
        f'<div class="sb-metric-mini-value">{format_vnd(S)}</div>'
        f'</div>'
        f'<div class="sb-metric-mini">'
        f'<div class="sb-metric-mini-label">Strike</div>'
        f'<div class="sb-metric-mini-value">{format_vnd(K)}</div>'
        f'</div>'
        f'<div class="sb-metric-mini">'
        f'<div class="sb-metric-mini-label">Giá CW</div>'
        f'<div class="sb-metric-mini-value" style="color:#FF6B35;">'
        f'{format_vnd(cw_price)}</div>'
        f'</div>'
        f'<div class="sb-metric-mini">'
        f'<div class="sb-metric-mini-label">S / K</div>'
        f'<div class="sb-metric-mini-value">{sk_ratio}</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; margin-top:6px; '
        f'padding:0 4px;">'
        f'<span style="font-size:0.68rem; color:#64748B;">'
        f"CR: <b style=\"color:#E2E8F0; font-family:'Fira Code',monospace;\">{cr:.1f}</b>"
        f'</span>'
        f'</div>'
        + position_html
        + f'<div class="sb-time-bar-wrapper">'
        f'<div class="sb-time-bar-header">'
        f'<span class="sb-time-bar-label">Thời gian còn lại</span>'
        f'<span class="sb-time-bar-value" style="color:{time_color};">{days}d</span>'
        f'</div>'
        f'<div class="sb-time-bar">'
        f'<div class="sb-time-bar-fill" style="width:{time_pct:.0f}%; '
        f'background:linear-gradient(90deg, {time_color}, {time_color}88);"></div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(dash_html, unsafe_allow_html=True)


# ============================================================
# SECTION 2: PORTFOLIO MANAGEMENT
# ============================================================

def _render_portfolio_section():
    """Render danh sách CW portfolio trong sidebar."""
    portfolio = st.session_state["cw_portfolio"]

    # Portfolio count badge
    count = len(portfolio)
    st.markdown(
        f'<div style="text-align:center;">'
        f'<div class="sb-portfolio-count-badge">'
        f'<span class="count-num">{count}</span> CW'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # CW cards
    for idx, cw in enumerate(portfolio):
        _render_cw_card(cw, idx)

    # Add CW button
    st.markdown("")
    if st.button("+ Thêm CW", use_container_width=True, key="sidebar_add_cw"):
        st.session_state["_show_add_form"] = not st.session_state.get("_show_add_form", False)
        st.rerun()

    # Show add form nếu đang mở
    if st.session_state.get("_show_add_form", False):
        _render_add_cw_form()

    # CSV upload in expander
    with st.expander("▤ Import CSV", expanded=False):
        uploaded = st.file_uploader(
            "Chọn file CSV",
            type=["csv"],
            key="sidebar_csv_upload",
            help="Upload file CSV để thêm nhiều CW cùng lúc",
            label_visibility="collapsed",
        )
        if uploaded is not None:
            _handle_csv_upload(uploaded)


def _render_cw_card(cw: dict, index: int):
    """Render professional CW card trong sidebar."""
    loai = "call" if cw["option_type"] == "call" else "put"
    badge_text = "CALL" if loai == "call" else "PUT"
    name = cw.get("ma_cw", f"CW #{index}").upper()
    editing_key = f"_editing_cw_{index}"
    is_editing = st.session_state.get(editing_key, False)
    is_selected = (index == st.session_state.get("selected_cw_index", -1))
    selected_class = "selected" if is_selected else ""

    # Position P&L
    entry_p = cw.get("entry_price")
    qty = cw.get("quantity")
    pnl_html = ""
    if entry_p and qty and entry_p > 0 and qty > 0:
        pnl_vnd = (cw["cw_price"] - entry_p) * qty
        pnl_pct = ((cw["cw_price"] / entry_p) - 1) * 100 if entry_p > 0 else 0
        pnl_color = "#22C55E" if pnl_vnd >= 0 else "#EF4444"
        pnl_sign = "+" if pnl_vnd >= 0 else ""
        pnl_html = (
            f'<div class="sb-cw-card-pnl" style="color:{pnl_color};">'
            f'{pnl_sign}{format_vnd(pnl_vnd)}đ ({pnl_sign}{pnl_pct:.1f}%) · {qty:,} CW'
            f'</div>'
        )

    st.markdown(
        f'<div class="sb-cw-card {selected_class}">'
        f'<div class="sb-cw-card-top">'
        f'<span class="sb-cw-card-name">{name}</span>'
        f'<span class="sb-cw-card-badge {loai}">{badge_text}</span>'
        f'</div>'
        f'<div class="sb-cw-card-stats">'
        f'<span class="sb-cw-card-stat">S={format_vnd(cw["S"])}</span>'
        f'<span class="sb-cw-card-stat">K={format_vnd(cw["K"])}</span>'
        f'<span class="sb-cw-card-stat">CW={format_vnd(cw["cw_price"])}</span>'
        f'<span class="sb-cw-card-stat">{cw.get("days_remaining", "?")}d</span>'
        f'</div>'
        f'{pnl_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Buttons: Edit + Xoá
    col_edit, col_del = st.columns(2)
    with col_edit:
        if st.button("∕ Sửa", key=f"edit_cw_{index}", use_container_width=True):
            st.session_state[editing_key] = not is_editing
            # Clear money-input cache so form shows fresh data
            _clear_money_cache(f"edit{index}")
            st.rerun()
    with col_del:
        if st.button("× Xoá", key=f"remove_cw_{index}", use_container_width=True):
            portfolio = st.session_state["cw_portfolio"]
            if index < len(portfolio):
                portfolio.pop(index)
                st.session_state["cw_portfolio"] = portfolio
                _auto_save_portfolio()
                st.rerun()

    # Inline edit form
    if is_editing:
        _render_edit_cw_form(cw, index)


def _render_edit_cw_form(cw: dict, index: int):
    """Form sửa CW inline trong sidebar."""
    prefix = f"edit{index}"
    editing_key = f"_editing_cw_{index}"

    with st.expander(f"∕ Sửa {cw.get('ma_cw', f'CW #{index}')}", expanded=True):
        ma_cw = st.text_input(
            "Mã CW", value=cw.get("ma_cw", ""),
            key=f"{prefix}_ma_cw",
        )
        ma_co_so = st.text_input(
            "Mã cơ sở", value=cw.get("ma_co_so", "N/A"),
            key=f"{prefix}_ma_cs",
        )

        c1, c2 = st.columns(2)
        with c1:
            S = _money_input(
                "Giá CS", cw["S"], 100, 10_000_000, 100,
                key=f"{prefix}_S",
            )
            K = _money_input(
                "Strike", cw["K"], 100, 10_000_000, 100,
                key=f"{prefix}_K",
            )
            cw_price = _money_input(
                "Giá CW", cw["cw_price"], 1, 1_000_000, 10,
                key=f"{prefix}_cw_price",
            )
        with c2:
            cr = st.number_input(
                "CR", value=float(cw["cr"]),
                min_value=0.01, max_value=100.0,
                step=0.01, format="%.2f",
                key=f"{prefix}_cr",
            )
            # Maturity date
            default_mat = cw.get("maturity_date")
            if not isinstance(default_mat, date):
                default_mat = date.today() + timedelta(
                    days=max(cw.get("days_remaining", 180), 1)
                )
            # Clamp expired maturity to tomorrow
            min_mat = date.today() + timedelta(days=1)
            if default_mat < min_mat:
                default_mat = min_mat
            maturity = st.date_input(
                "Đáo hạn", value=default_mat,
                min_value=min_mat,
                key=f"{prefix}_maturity", format="DD/MM/YYYY",
            )
            sigma = st.number_input(
                "Vol (%)", value=float(cw["sigma"] * 100),
                min_value=1.0, max_value=200.0,
                step=0.5, format="%.1f",
                key=f"{prefix}_sigma",
            ) / 100.0

        option_type = st.radio(
            "Loại", ["Call", "Put"],
            index=0 if cw["option_type"] == "call" else 1,
            horizontal=True, key=f"{prefix}_type",
        )

        ce1, ce2 = st.columns(2)
        with ce1:
            r_val = st.number_input(
                "Lãi suất (%)", value=float(cw["r"] * 100),
                min_value=0.0, max_value=15.0,
                step=0.1, format="%.1f",
                key=f"{prefix}_r",
            ) / 100.0
        with ce2:
            q_val = st.number_input(
                "Cổ tức (%)", value=float(cw.get("q", 0) * 100),
                min_value=0.0, max_value=20.0,
                step=0.5, format="%.1f",
                key=f"{prefix}_q",
                help="Tỷ suất cổ tức hàng năm",
            ) / 100.0

        _issuer_options = ["—", "KIS", "VND", "HSC", "MBS", "BSC", "SSI", "VNDS", "ACBS", "Khác"]
        _cur_issuer = cw.get("issuer", "")
        _issuer_idx = _issuer_options.index(_cur_issuer) if _cur_issuer in _issuer_options else 0
        issuer = st.selectbox("TCPH", options=_issuer_options, index=_issuer_idx,
                              key=f"{prefix}_issuer")

        # Position Tracking
        with st.expander("▪ Vị Thế (Position)", expanded=False):
            pos_c1, pos_c2 = st.columns(2)
            with pos_c1:
                _existing_entry = cw.get("entry_price") or 0
                entry_price = _money_input(
                    "Giá vào lệnh", _existing_entry, 0, 1_000_000, 10,
                    key=f"{prefix}_entry_price",
                    help_text="Giá trung bình mua vào (0 = chưa mua)",
                )
            with pos_c2:
                _existing_qty = cw.get("quantity") or 0
                quantity = int(_money_input(
                    "Số lượng", _existing_qty, 0, 10_000_000, 100,
                    key=f"{prefix}_quantity",
                    help_text="Số CW đang nắm giữ",
                ))

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("▪ Lưu", key=f"{prefix}_save", use_container_width=True):
                T = max((maturity - date.today()).days / 365.0, 0.001)
                days_rem = max((maturity - date.today()).days, 0)
                updated = {
                    "ma_cw": ma_cw or cw.get("ma_cw", "N/A"),
                    "ma_co_so": ma_co_so or "N/A",
                    "S": S, "K": K, "T": T, "r": r_val, "sigma": sigma,
                    "q": q_val,
                    "cr": float(cr), "cw_price": cw_price,
                    "option_type": option_type.lower(),
                    "maturity_date": maturity,
                    "days_remaining": days_rem,
                    "issuer": issuer if issuer != "—" else "",
                    "entry_price": entry_price if entry_price > 0 else None,
                    "quantity": quantity if quantity > 0 else None,
                    "_source": cw.get("_source", "manual"),
                }

                portfolio = st.session_state["cw_portfolio"]
                if index < len(portfolio):
                    portfolio[index] = updated
                    st.session_state["cw_portfolio"] = portfolio
                    st.session_state[editing_key] = False
                    _clear_money_cache(prefix)
                    _auto_save_portfolio()
                    st.rerun()

        with col_cancel:
            if st.button("× Huỷ", key=f"{prefix}_cancel", use_container_width=True):
                st.session_state[editing_key] = False
                _clear_money_cache(prefix)
                st.rerun()


def _render_add_cw_form():
    """Form thêm CW mới vào portfolio."""
    with st.expander("▹ Nhập CW Mới", expanded=True):
        ma_cw = st.text_input("Mã CW", key="add_ma_cw", placeholder="CVPB2401")
        ma_co_so = st.text_input("Mã cổ phiếu cơ sở", key="add_ma_cs", placeholder="VPB")

        c1, c2 = st.columns(2)
        with c1:
            S = _money_input("Giá CS (VNĐ)", 20_000, 100, 10_000_000, 100, key="add_S")
            K = _money_input("Strike (VNĐ)", 18_000, 100, 10_000_000, 100, key="add_K")
            cw_price = _money_input("Giá CW (VNĐ)", 1_000, 1, 1_000_000, 10, key="add_cw_price")
        with c2:
            cr = st.number_input("CR", value=2.0, min_value=0.01, max_value=100.0,
                                 step=0.01, format="%.2f", key="add_cr")
            maturity = st.date_input("Đáo hạn", value=date.today() + timedelta(days=180),
                                     min_value=date.today() + timedelta(days=1),
                                     key="add_maturity", format="DD/MM/YYYY")
            sigma = st.number_input("Vol (%)", value=35.0, min_value=1.0, max_value=200.0,
                                    step=0.5, format="%.1f", key="add_sigma") / 100.0

        option_type = st.radio("Loại", ["Call", "Put"], horizontal=True, key="add_type")

        c3, c4 = st.columns(2)
        with c3:
            r_val = st.number_input("Lãi suất (%)", value=3.0, min_value=0.0, max_value=15.0,
                                    step=0.1, format="%.1f", key="add_r") / 100.0
        with c4:
            q_val = st.number_input("Cổ tức (%)", value=0.0, min_value=0.0, max_value=20.0,
                                    step=0.5, format="%.1f", key="add_q",
                                    help="Tỷ suất cổ tức hàng năm của cổ phiếu cơ sở") / 100.0

        issuer = st.selectbox("TCPH (Tổ Chức Phát Hành)", options=[
            "—", "KIS", "VND", "HSC", "MBS", "BSC", "SSI", "VNDS", "ACBS", "Khác"
        ], key="add_issuer", help="Tổ chức phát hành chứng quyền")

        # Position Tracking — optional
        with st.expander("▪ Vị Thế (Position)", expanded=False):
            pos_c1, pos_c2 = st.columns(2)
            with pos_c1:
                entry_price = _money_input(
                    "Giá vào lệnh (VNĐ)", 0, 0, 1_000_000, 10,
                    key="add_entry_price",
                    help_text="Giá trung bình mua vào (0 = chưa mua)",
                )
            with pos_c2:
                quantity = int(_money_input(
                    "Số lượng", 0, 0, 10_000_000, 100,
                    key="add_quantity",
                    help_text="Số lượng CW đang nắm giữ (0 = chưa mua)",
                ))

        if st.button("✓ Xác Nhận Thêm CW", use_container_width=True, key="confirm_add_cw"):
            if ma_cw:
                T = max((maturity - date.today()).days / 365.0, 0.001)
                days_rem = max((maturity - date.today()).days, 0)
                new_entry = {
                    "ma_cw": ma_cw,
                    "ma_co_so": ma_co_so or "N/A",
                    "S": S, "K": K, "T": T, "r": r_val, "sigma": sigma,
                    "q": q_val,
                    "cr": float(cr), "cw_price": cw_price,
                    "option_type": option_type.lower(),
                    "maturity_date": maturity,
                    "days_remaining": days_rem,
                    "issuer": issuer if issuer != "—" else "",
                    "entry_price": entry_price if entry_price > 0 else None,
                    "quantity": quantity if quantity > 0 else None,
                    "_source": "manual",
                }
                st.session_state["cw_portfolio"].append(new_entry)
                st.session_state["_show_add_form"] = False
                # Clear money-input cache for add form
                for suffix in ["_S", "_K", "_cw_price", "_entry_price", "_quantity"]:
                    st.session_state.pop(f"_money_add{suffix}", None)
                    st.session_state.pop(f"add{suffix}", None)
                _auto_save_portfolio()
                st.rerun()
            else:
                st.warning("Vui lòng nhập Mã CW")


def _handle_csv_upload(uploaded_file):
    """Parse CSV và thêm các entries vào cw_portfolio."""
    from data.csv_handler import parse_csv

    result = parse_csv(uploaded_file)
    if result is None:
        return

    df, errors = result
    if df is None:
        for err in errors:
            st.error(err)
        return

    if errors:
        for err in errors:
            st.warning(err)

    count = 0
    for _, row in df.iterrows():
        T_val = float(row["T"])
        entry = {
            "ma_cw": str(row["ma_cw"]),
            "ma_co_so": str(row["ma_co_so"]),
            "S": float(row["gia_co_so"]),
            "K": float(row["gia_thuc_hien"]),
            "T": T_val,
            "r": float(row.get("lai_suat_phi_rui_ro", 0.03)),
            "sigma": float(row.get("bien_do_gia", 0.30)),
            "q": float(row.get("co_tuc", 0.0)),
            "cr": float(row["ty_le_chuyen_doi"]),
            "cw_price": float(row["gia_cw"]),
            "option_type": str(row["loai_cw"]),
            "days_remaining": max(int(T_val * 365), 0),
            "_source": "csv_upload",
        }
        # Lưu maturity_date cho JSON serialization
        if "ngay_dao_han" in row:
            try:
                entry["maturity_date"] = row["ngay_dao_han"]
            except Exception:
                pass

        st.session_state["cw_portfolio"].append(entry)
        count += 1

    if count > 0:
        st.success(f"Đã thêm {count} CW từ CSV")
        _auto_save_portfolio()
        st.rerun()


# ============================================================
# SECTION 3: SAVE / LOAD
# ============================================================

def _render_save_load_section():
    """Render phần Lưu/Tải portfolio trong sidebar."""
    from data.portfolio_manager import (
        list_portfolios, save_portfolio, load_portfolio,
        delete_portfolio, deserialize_cw_entry,
    )

    portfolios = list_portfolios()

    # Tải
    if portfolios:
        selected = st.selectbox(
            "Chọn portfolio",
            options=portfolios,
            key="sidebar_portfolio_select",
            label_visibility="collapsed",
        )

        col_load, col_del = st.columns(2)
        with col_load:
            if st.button("▤ Tải", use_container_width=True, key="btn_load_portfolio"):
                data = load_portfolio(selected)
                if data:
                    _apply_loaded_portfolio(data)
                    st.success(f"Đã tải: {data['portfolio_name']}")
                    st.rerun()
        with col_del:
            if st.button("× Xoá", use_container_width=True, key="btn_del_portfolio"):
                delete_portfolio(selected)
                st.rerun()
    else:
        _render_empty_state(
            "▤",
            "Chưa có portfolio",
            "Lưu portfolio để sử dụng lại sau.",
        )

    # Lưu
    st.markdown("")
    save_name = st.text_input(
        "Tên portfolio",
        value="My Portfolio",
        key="sidebar_save_name",
        label_visibility="collapsed",
        placeholder="Nhập tên portfolio...",
    )
    if st.button("▪ Lưu Portfolio", use_container_width=True, key="btn_save_portfolio"):
        portfolio = st.session_state.get("cw_portfolio", [])
        if portfolio:
            save_portfolio(save_name, portfolio)
            st.success(f"Đã lưu: {save_name}")
            st.rerun()


def _auto_save_portfolio():
    """Auto-save portfolio vào default.json (khi add/remove/CSV)."""
    from data.portfolio_manager import save_portfolio

    portfolio = st.session_state.get("cw_portfolio", [])
    if portfolio:
        save_portfolio("Default", portfolio, filename="default")


def _apply_loaded_portfolio(data: dict):
    """Áp dụng dữ liệu portfolio đã load vào session_state."""
    from data.portfolio_manager import deserialize_cw_entry

    all_cw = []
    for cw_data in data.get("cw_list", []):
        all_cw.append(deserialize_cw_entry(cw_data))

    # Lưu trực tiếp vào cw_portfolio để sidebar nhận ngay lập tức
    st.session_state["cw_portfolio"] = all_cw


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def format_vnd(value: float) -> str:
    """Format số tiền VNĐ với dấu phẩy ngăn cách."""
    if value == 0:
        return "0"
    if abs(value) >= 1:
        return f"{value:,.0f}"
    elif abs(value) >= 0.01:
        return f"{value:,.2f}"
    else:
        return f"{value:,.4f}"


def format_pct(value: float, decimals: int = 2) -> str:
    """Format phần trăm."""
    return f"{value:.{decimals}f}%"


def colored_metric(label, value, color="white", delta=None, delta_color=None):
    """Metric card có màu tùy chỉnh, hỗ trợ delta."""
    delta_html = ""
    if delta is not None:
        d_color = delta_color or ("#22C55E" if "+" in str(delta) else "#EF4444")
        delta_html = (
            f'<div style="font-size:0.75rem; color:{d_color}; '
            f'margin-top:2px;">{delta}</div>'
        )
    st.markdown(
        f'<div class="custom-metric">'
        f'<div class="custom-metric-label">{label}</div>'
        f'<div class="custom-metric-value" style="color: {color};">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# UI HELPER FUNCTIONS (v2)
# ============================================================

def chart_container(title: str = ""):
    """Mở container card cho chart. Gọi chart_container_end() sau st.plotly_chart()."""
    html = '<div class="chart-container">'
    if title:
        html += f'<div class="chart-container-title">{title}</div>'
    st.markdown(html, unsafe_allow_html=True)


def chart_container_end():
    """Đóng container chart."""
    st.markdown('</div>', unsafe_allow_html=True)


def section_divider(thick: bool = False):
    """Divider gradient thay cho st.markdown('---')."""
    cls = "section-divider-thick" if thick else "section-divider"
    st.markdown(f'<div class="{cls}"></div>', unsafe_allow_html=True)


def tab_empty_state(icon: str, title: str, text: str, hint: str = ""):
    """Empty state đẹp cho tabs khi chưa chọn CW."""
    hint_html = ""
    if hint:
        hint_html = f'<div class="tab-empty-state-hint">{hint}</div>'
    st.markdown(
        f'<div class="tab-empty-state">'
        f'<div class="tab-empty-state-icon">{icon}</div>'
        f'<div class="tab-empty-state-title">{title}</div>'
        f'<div class="tab-empty-state-text">{text}</div>'
        f'{hint_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def table_container(title: str = "", badge: str = ""):
    """Mở container card cho bảng dữ liệu."""
    badge_html = ""
    if badge:
        badge_html = f'<span class="table-container-badge">{badge}</span>'
    st.markdown(
        f'<div class="table-container">'
        f'<div class="table-container-header">'
        f'<span class="table-container-title">{title}</span>'
        f'{badge_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def table_container_end():
    """Đóng container bảng."""
    st.markdown('</div>', unsafe_allow_html=True)


def status_badge(text: str, variant: str) -> str:
    """Trả về HTML cho status badge. variant: premium|discount|fair."""
    return f'<span class="status-badge {variant}">{text}</span>'
