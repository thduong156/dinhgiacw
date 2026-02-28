"""Tab: Theo Dõi & Backtest — Daily Data Tracker + Backtest giá lý thuyết vs thị trường."""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from ui.components import (
    format_vnd, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end, render_table,
)
from ui.charts import (
    create_daily_price_chart, create_daily_pd_chart,
    create_daily_greeks_chart, create_backtesting_chart,
    create_backtest_price_chart, create_backtest_pd_chart,
)
from data.daily_tracker import (
    save_daily_record, load_daily_history, get_all_tracked_cw,
    get_latest_record, delete_daily_record, delete_all_history,
    export_history_csv, compute_auto_fields,
)
from data.portfolio_manager import save_portfolio


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _auto_save_portfolio():
    """Tự động lưu portfolio hiện tại ra default.json."""
    portfolio = st.session_state.get("cw_portfolio", [])
    save_portfolio("Default", portfolio, "default")


def _fmt_date(date_str):
    """Chuyển YYYY-MM-DD → DD/MM/YY cho hiển thị."""
    if not date_str:
        return "N/A"
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%y")
    except (ValueError, TypeError):
        return date_str


def _fmt_number(val):
    """Format số với dấu phẩy phân cách hàng nghìn."""
    if val is None or val == 0:
        return "0"
    return f"{val:,.0f}"


def _parse_number(text):
    """Parse số từ text có dấu phẩy/chấm phân cách."""
    cleaned = text.replace(",", "").replace(" ", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _build_cw_options():
    """
    Xây danh sách CW options từ portfolio + CW có history.
    Returns: list of (label, ma_cw, source_info)
    """
    portfolio = st.session_state.get("cw_portfolio", [])
    tracked = set(get_all_tracked_cw())

    options = []
    seen_codes = set()

    # 1) CW từ portfolio
    for cw in portfolio:
        ma = cw.get("ma_cw", "N/A").upper()
        cs = cw.get("ma_co_so", "N/A").upper()
        loai = "CALL" if cw.get("option_type") == "call" else "PUT"
        label = f"{ma} | {cs} | {loai}"
        options.append((label, ma, "portfolio"))
        seen_codes.add(ma)

    # 2) CW có history nhưng không trong portfolio
    for ma in tracked:
        if ma.upper() not in seen_codes:
            options.append((f"{ma} (chỉ có lịch sử)", ma, "history_only"))

    return options


def _get_cw_static_from_portfolio(ma_cw: str) -> dict:
    """Lấy static params (K, cr, option_type, maturity_date, r) từ portfolio."""
    portfolio = st.session_state.get("cw_portfolio", [])
    for cw in portfolio:
        if cw.get("ma_cw", "").upper() == ma_cw.upper():
            mat = cw.get("maturity_date", "")
            if isinstance(mat, date):
                mat = mat.strftime("%d/%m/%Y")
            return {
                "ma_co_so": cw.get("ma_co_so", "N/A"),
                "K": cw.get("K", 0),
                "cr": cw.get("cr", 1),
                "option_type": cw.get("option_type", "call"),
                "maturity_date": mat,
                "r": cw.get("r", 0.03),
                "sigma": cw.get("sigma", 0.30),
            }
    # Fallback: try history file
    data = load_daily_history(ma_cw)
    if data:
        return {
            "ma_co_so": data.get("ma_co_so", "N/A"),
            "K": data.get("K", 0),
            "cr": data.get("cr", 1),
            "option_type": data.get("option_type", "call"),
            "maturity_date": data.get("maturity_date", ""),
            "r": data.get("r", 0.03),
            "sigma": 0.30,
        }
    return {}


def _get_portfolio_defaults(ma_cw: str) -> dict:
    """Lấy giá trị S, cw_price, sigma mới nhất từ portfolio entry."""
    portfolio = st.session_state.get("cw_portfolio", [])
    for cw in portfolio:
        if cw.get("ma_cw", "").upper() == ma_cw.upper():
            return {
                "S": cw.get("S", 0.0),
                "cw_price": cw.get("cw_price", 0.0),
                "sigma": cw.get("sigma", 0.30),
            }
    return {"S": 0.0, "cw_price": 0.0, "sigma": 0.30}


def _update_portfolio_entry(ma_cw: str, S: float, cw_price: float, sigma: float):
    """Cập nhật CW entry trong portfolio với giá mới nhất."""
    portfolio = st.session_state.get("cw_portfolio", [])
    for i, cw in enumerate(portfolio):
        if cw.get("ma_cw", "").upper() == ma_cw.upper():
            portfolio[i]["S"] = S
            portfolio[i]["cw_price"] = cw_price
            portfolio[i]["sigma"] = sigma
            st.session_state["cw_portfolio"] = portfolio
            _auto_save_portfolio()
            return True
    return False


def _trend_badge(current, previous):
    """Trả về HTML trend badge (up/down/flat)."""
    if current is None or previous is None:
        return ""
    if current > previous * 1.001:
        return '<span class="trend-badge up">▲ Tăng</span>'
    elif current < previous * 0.999:
        return '<span class="trend-badge down">▼ Giảm</span>'
    else:
        return '<span class="trend-badge flat">― Ngang</span>'


# ============================================================
# RENDER TAB CHÍNH
# ============================================================

def render_daily_tracker_tab():
    """Tab 9: Theo dõi dữ liệu hàng ngày cho từng CW."""
    section_title("⊡", "Theo Dõi Dữ Liệu Hàng Ngày")

    st.markdown(
        '<div class="info-box">'
        'Nhập dữ liệu <b>hàng ngày</b> (giá, biến động) cho từng CW. '
        'App tự động tính <b>giá lý thuyết, Greeks, P/D%, score</b> và lưu lịch sử. '
        'Dữ liệu được dùng cho <b>biểu đồ xu hướng, backtesting</b> và '
        '<b>cải thiện Markowitz</b> (Tab Đề Xuất CW).'
        '</div>',
        unsafe_allow_html=True,
    )

    # ===== CW SELECTOR =====
    cw_options = _build_cw_options()

    if not cw_options:
        tab_empty_state(
            "⊡",
            "Chưa Có CW Nào Trong Portfolio",
            "Thêm CW vào portfolio ở Sidebar trước, sau đó quay lại đây "
            "để bắt đầu theo dõi dữ liệu hàng ngày.",
            "Sidebar → Thêm CW hoặc Import CSV",
        )
        return

    labels = [opt[0] for opt in cw_options]
    selected_idx = st.selectbox(
        "Chọn CW để theo dõi",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key="_daily_cw_selector",
    )

    selected_label, selected_ma, selected_source = cw_options[selected_idx]
    cw_static = _get_cw_static_from_portfolio(selected_ma)

    if not cw_static:
        st.warning(f"Không tìm thấy thông tin static cho **{selected_ma}**.")
        return

    # Quick info bar
    st.markdown(
        f'<div style="font-size:0.8rem; color:#94A3B8; margin-bottom:12px;">'
        f'Mã CS: <b style="color:#F1F5F9;">{cw_static.get("ma_co_so", "N/A")}</b> | '
        f'Strike: <b style="color:#F1F5F9;">{format_vnd(cw_static.get("K", 0))} đ</b> | '
        f'Loại: <b style="color:#F1F5F9;">{cw_static.get("option_type", "call").upper()}</b> | '
        f'CR: <b style="color:#F1F5F9;">{cw_static.get("cr", 1)}</b> | '
        f'Đáo hạn: <b style="color:#F1F5F9;">{cw_static.get("maturity_date", "N/A")}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

    section_divider(thick=True)

    # ===== DAILY INPUT FORM =====
    section_title("▹", "Nhập Dữ Liệu Hàng Ngày")

    defaults = _get_portfolio_defaults(selected_ma)

    with st.form(key="_daily_input_form", clear_on_submit=False):
        col_date, col_s, col_cw, col_sigma = st.columns(4)

        with col_date:
            input_date_str = st.text_input(
                "⊡ Ngày",
                value=date.today().strftime("%d/%m/%y"),
                help="DD/MM/YY — VD: 18/02/26",
            )

        with col_s:
            input_S_str = st.text_input(
                "◆ Giá Cơ Sở (S)",
                value=_fmt_number(defaults["S"]),
                help="Giá cổ phiếu cơ sở — VD: 100,000",
            )

        with col_cw:
            input_cw_str = st.text_input(
                "▪ Giá CW",
                value=_fmt_number(defaults["cw_price"]),
                help="Giá CW trên sàn — VD: 3,800",
            )

        with col_sigma:
            input_sigma_str = st.text_input(
                "▪ σ (%)",
                value=f"{defaults['sigma'] * 100:.1f}",
                help="Biến động lịch sử — VD: 35.0",
            )

        col_sync, col_submit = st.columns([2, 1])
        with col_sync:
            auto_sync = st.checkbox(
                "↻ Tự động cập nhật Portfolio",
                value=True,
                help="S, Giá CW, sigma sẽ được cập nhật vào portfolio khi lưu",
            )
        with col_submit:
            submitted = st.form_submit_button(
                "▪ Lưu Dữ Liệu", use_container_width=True,
            )

    if submitted:
        # Parse inputs từ text
        input_S = _parse_number(input_S_str)
        input_cw_price = _parse_number(input_cw_str)
        try:
            input_sigma_pct = float(input_sigma_str.replace(",", ".").strip())
        except (ValueError, TypeError):
            input_sigma_pct = defaults["sigma"] * 100

        # Parse date DD/MM/YY
        input_date = None
        for fmt in ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                input_date = datetime.strptime(input_date_str.strip(), fmt).date()
                break
            except ValueError:
                continue

        if input_date is None:
            st.error("× Định dạng ngày không hợp lệ. Nhập **DD/MM/YY** (VD: 18/02/26)")
        elif input_S <= 0 or input_cw_price <= 0:
            st.error("× Giá cơ sở và giá CW phải lớn hơn 0.")
        else:
            sigma_decimal = input_sigma_pct / 100.0
            date_str = input_date.strftime("%Y-%m-%d")

            daily_input = {
                "date": date_str,
                "S": input_S,
                "cw_price": input_cw_price,
                "sigma": sigma_decimal,
            }

            # Compute auto fields
            auto_fields = compute_auto_fields(cw_static, daily_input)
            record = {**daily_input, **auto_fields}

            # Save
            save_daily_record(selected_ma, cw_static, record)

            # Auto-sync portfolio
            if auto_sync:
                _update_portfolio_entry(selected_ma, input_S, input_cw_price, sigma_decimal)

            # Success message
            theo = auto_fields.get("theoretical_price")
            pd_pct = auto_fields.get("premium_discount_pct")
            score = auto_fields.get("score")

            msg = f"✓ Đã lưu **{input_date.strftime('%d/%m/%y')}** — **{selected_ma}**"
            if theo:
                msg += f" | LT: **{format_vnd(theo)} đ**"
            if pd_pct is not None:
                msg += f" | P/D: **{pd_pct:+.2f}%**"
            if score is not None:
                msg += f" | Score: **{int(score)}/100**"
            st.success(msg)

    # ===== LOAD HISTORY =====
    section_divider()

    history_data = load_daily_history(selected_ma)
    records = history_data.get("records", []) if history_data else []

    if not records:
        tab_empty_state(
            "⊡",
            "Chưa Có Dữ Liệu Lịch Sử",
            f"Nhập dữ liệu cho **{selected_ma}** ở form bên trên. "
            "Hệ thống sẽ tự động tính giá lý thuyết, Greeks và score.",
            "Nhập Ngày, S, Giá CW, σ% → Lưu Dữ Liệu",
        )
        return

    # ===== SUMMARY STATS =====
    if len(records) >= 2:
        section_title("▪", "Tổng Quan")

        first_rec = records[0]
        last_rec = records[-1]
        n_days = len(records)

        # CW Price trend
        cw_first = first_rec.get("cw_price", 0)
        cw_last = last_rec.get("cw_price", 0)
        cw_change_pct = ((cw_last - cw_first) / cw_first * 100) if cw_first > 0 else 0
        trend_html = _trend_badge(cw_last, cw_first)

        # Averages
        pd_vals = [r.get("premium_discount_pct", 0) for r in records if r.get("premium_discount_pct") is not None]
        avg_pd = sum(pd_vals) / len(pd_vals) if pd_vals else 0
        pd_color = "#22C55E" if avg_pd < 0 else "#EF4444" if avg_pd > 0 else "#93C5FD"

        score_vals = [r.get("score", 0) for r in records if r.get("score") is not None]
        avg_score = int(sum(score_vals) / len(score_vals)) if score_vals else 0
        score_color = "#22C55E" if avg_score >= 65 else "#F59E0B" if avg_score >= 50 else "#EF4444"

        st.markdown(
            f'<div class="daily-stats-grid">'
            f'<div class="daily-stat-card">'
            f'<div class="daily-stat-card-value" style="color:#FF6B35;">{n_days}</div>'
            f'<div class="daily-stat-card-label">Ngày Theo Dõi</div></div>'
            f'<div class="daily-stat-card">'
            f'<div class="daily-stat-card-value" style="color:#F1F5F9;">'
            f'{format_vnd(cw_last)} đ</div>'
            f'<div class="daily-stat-card-label">Giá CW ({cw_change_pct:+.1f}%) {trend_html}</div></div>'
            f'<div class="daily-stat-card">'
            f'<div class="daily-stat-card-value" style="color:{pd_color};">'
            f'{avg_pd:+.2f}%</div>'
            f'<div class="daily-stat-card-label">P/D Trung Bình</div></div>'
            f'<div class="daily-stat-card">'
            f'<div class="daily-stat-card-value" style="color:{score_color};">'
            f'{avg_score}</div>'
            f'<div class="daily-stat-card-label">Score Trung Bình</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        section_divider()

    # ===== TREND CHARTS =====
    if len(records) >= 2:
        section_title("△", "Biểu Đồ Xu Hướng")

        chart_row1_col1, chart_row1_col2 = st.columns(2)

        with chart_row1_col1:
            chart_container("Biến Động Giá")
            fig_price = create_daily_price_chart(records)
            st.plotly_chart(fig_price, use_container_width=True)
            chart_container_end()

        with chart_row1_col2:
            chart_container("Premium / Discount %")
            fig_pd = create_daily_pd_chart(records)
            st.plotly_chart(fig_pd, use_container_width=True)
            chart_container_end()

        chart_row2_col1, chart_row2_col2 = st.columns(2)

        with chart_row2_col1:
            chart_container("Backtesting — Lý Thuyết vs Thực Tế")
            fig_bt = create_backtesting_chart(records)
            st.plotly_chart(fig_bt, use_container_width=True)
            chart_container_end()

        with chart_row2_col2:
            chart_container("Greeks & Đòn Bẩy")
            fig_greeks = create_daily_greeks_chart(records)
            st.plotly_chart(fig_greeks, use_container_width=True)
            chart_container_end()

        section_divider()

    # ===== HISTORY TABLE =====
    section_title("≡", "Lịch Sử Dữ Liệu")

    display_rows = []
    for r in reversed(records):  # Most recent first
        display_rows.append({
            "Ngày": _fmt_date(r.get("date", "")),
            "S (đ)": format_vnd(r.get("S", 0)),
            "Giá CW (đ)": format_vnd(r.get("cw_price", 0)),
            "Giá LT (đ)": format_vnd(r.get("theoretical_price", 0)) if r.get("theoretical_price") else "N/A",
            "P/D %": f"{r.get('premium_discount_pct', 0):+.2f}%" if r.get("premium_discount_pct") is not None else "N/A",
            "Delta": f"{r.get('delta', 0):.4f}" if r.get("delta") is not None else "N/A",
            "Score": int(r["score"]) if r.get("score") is not None else "N/A",
        })

    display_df = pd.DataFrame(display_rows)
    table_container("Lịch Sử Dữ Liệu", badge=f"{len(records)} ngày")
    render_table(display_df)
    table_container_end()

    # ===== EXPORT & MANAGE =====
    section_divider()
    section_title("⚙", "Quản Lý Dữ Liệu")

    col_export, col_delete_one, col_delete_all = st.columns(3)

    with col_export:
        csv_str = export_history_csv(selected_ma)
        if csv_str:
            st.download_button(
                label="↓ Tải Lịch Sử (CSV)",
                data=csv_str.encode("utf-8"),
                file_name=f"daily_{selected_ma}.csv",
                mime="text/csv",
                key="_daily_export_csv",
            )

    with col_delete_one:
        if records:
            date_labels = [
                f"{_fmt_date(r.get('date', ''))} — CW: {format_vnd(r.get('cw_price', 0))}"
                for r in reversed(records)
            ]
            date_values = [r.get("date", "") for r in reversed(records)]
            del_idx = st.selectbox(
                "Chọn ngày để xóa",
                range(len(date_labels)),
                format_func=lambda i: date_labels[i],
                key="_daily_del_date",
            )
            if st.button("× Xóa Ngày Này", key="_daily_del_btn"):
                del_date = date_values[del_idx]
                if delete_daily_record(selected_ma, del_date):
                    st.success(f"Đã xóa record ngày {_fmt_date(del_date)}.")
                    st.rerun()
                else:
                    st.error("Không thể xóa record.")

    with col_delete_all:
        st.markdown("")
        st.markdown("")
        if st.button("△ Xóa Toàn Bộ Lịch Sử", key="_daily_del_all", type="secondary"):
            st.session_state["_daily_confirm_delete"] = True

        if st.session_state.get("_daily_confirm_delete"):
            st.warning(f"Xóa **toàn bộ {len(records)} ngày** dữ liệu của **{selected_ma}**?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✓ Xác Nhận Xóa", key="_daily_confirm_yes"):
                    delete_all_history(selected_ma)
                    st.session_state["_daily_confirm_delete"] = False
                    st.success(f"Đã xóa toàn bộ lịch sử {selected_ma}.")
                    st.rerun()
            with c2:
                if st.button("× Hủy", key="_daily_confirm_no"):
                    st.session_state["_daily_confirm_delete"] = False
                    st.rerun()

    # ===== BULK IMPORT =====
    section_divider()

    with st.expander("↑ Nhập Dữ Liệu Hàng Loạt (CSV)", expanded=False):
        st.markdown(
            '<div class="info-box">'
            'Upload file CSV với các cột: <b>date, S, cw_price, sigma</b>. '
            'Format ngày: <b>DD/MM/YYYY</b> hoặc <b>YYYY-MM-DD</b>. '
            'Sigma tính theo % (VD: 35 = 35%).'
            '</div>',
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Chọn file CSV",
            type=["csv"],
            key="_daily_bulk_upload",
        )

        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                required_cols = ["date", "S", "cw_price"]
                missing = [c for c in required_cols if c not in df.columns]

                if missing:
                    st.error(f"Thiếu cột: {', '.join(missing)}")
                else:
                    success_count = 0
                    error_count = 0

                    for _, row in df.iterrows():
                        try:
                            # Parse date
                            date_raw = str(row["date"]).strip()
                            try:
                                parsed_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
                            except ValueError:
                                try:
                                    parsed_date = datetime.strptime(date_raw, "%d/%m/%Y").date()
                                except ValueError:
                                    parsed_date = datetime.strptime(date_raw, "%d/%m/%y").date()

                            sigma_val = float(row.get("sigma", defaults["sigma"] * 100))
                            if sigma_val > 1:
                                sigma_val = sigma_val / 100.0

                            daily_input = {
                                "date": parsed_date.strftime("%Y-%m-%d"),
                                "S": float(row["S"]),
                                "cw_price": float(row["cw_price"]),
                                "sigma": sigma_val,
                            }

                            auto_fields = compute_auto_fields(cw_static, daily_input)
                            record = {**daily_input, **auto_fields}
                            save_daily_record(selected_ma, cw_static, record)
                            success_count += 1

                        except Exception:
                            error_count += 1

                    st.success(
                        f"✓ Import hoàn tất: **{success_count}** records thành công"
                        + (f", **{error_count}** lỗi" if error_count > 0 else "")
                    )

                    if success_count > 0:
                        st.rerun()

            except Exception as e:
                st.error(f"Lỗi đọc file CSV: {e}")

    # ============================================================
    # BACKTEST SECTION
    # ============================================================
    _render_backtest_section()


def _render_backtest_section():
    """Phần Backtest: so sánh Giá Lý Thuyết vs Giá Thị Trường theo lịch sử."""
    import numpy as np
    import pandas as pd
    from data.daily_tracker import get_all_tracked_cw, get_history_dataframe

    st.markdown("---")
    section_title("⊞", "Backtest — Giá Lý Thuyết vs Thị Trường")

    all_tracked = get_all_tracked_cw()
    if not all_tracked:
        tab_empty_state(
            "⊞",
            "Chưa có dữ liệu để Backtest",
            "Nhập ít nhất 2 ngày dữ liệu ở phần Theo Dõi bên trên để bật Backtest.",
            "Nhập dữ liệu → Lưu → Quay lại đây",
        )
        return

    # CW selector
    col_sel, _ = st.columns([2, 3])
    with col_sel:
        selected_bt = st.selectbox(
            "Chọn CW để Backtest",
            all_tracked,
            key="backtest_cw_selector",
        )

    df_full = get_history_dataframe(selected_bt)
    if df_full is None or len(df_full) < 2:
        st.warning(
            f"CW **{selected_bt}** chỉ có "
            f"{'0' if df_full is None else len(df_full)} ngày dữ liệu. "
            "Cần ít nhất 2 ngày."
        )
        return

    required = {"date", "cw_price", "theoretical_price"}
    if not required.issubset(df_full.columns):
        st.error("Dữ liệu thiếu cột bắt buộc. Hãy đảm bảo các bản ghi đã được tính toán đầy đủ.")
        return

    # Date range filter
    section_divider()
    min_date = df_full["date"].min().date()
    max_date = df_full["date"].max().date()
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        start_date = st.date_input("Từ ngày", value=min_date,
                                   min_value=min_date, max_value=max_date,
                                   key="bt_start_date")
    with c2:
        end_date = st.date_input("Đến ngày", value=max_date,
                                 min_value=min_date, max_value=max_date,
                                 key="bt_end_date")

    df = df_full[
        (df_full["date"].dt.date >= start_date) &
        (df_full["date"].dt.date <= end_date)
    ].copy()

    if len(df) < 2:
        st.warning("Khoảng ngày có ít hơn 2 records. Hãy mở rộng khoảng thời gian.")
        return

    # Metrics
    mae = float(np.mean(np.abs(df["theoretical_price"] - df["cw_price"])))
    corr = float(df["theoretical_price"].corr(df["cw_price"]))
    avg_pd = float(df["premium_discount_pct"].mean()) if "premium_discount_pct" in df.columns else 0.0

    section_divider()
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        colored_metric("Số Ngày Dữ Liệu", f"{len(df)} ngày", "#B8C2DB")
    with m2:
        colored_metric("MAE (Sai Số TB)", f"{mae:,.2f} đ", "#FFE66D")
    with m3:
        sign = "+" if avg_pd >= 0 else ""
        colored_metric("P/D % Trung Bình", f"{sign}{avg_pd:.2f}%",
                       "#2ECC71" if avg_pd >= 0 else "#E74C3C")
    with m4:
        colored_metric("Tương Quan (ρ)", f"{corr:.4f}",
                       "#2ECC71" if corr >= 0.85 else ("#FFE66D" if corr >= 0.6 else "#E74C3C"))

    section_divider()

    # Chart chính
    chart_container("So Sánh Giá: Thị Trường vs Lý Thuyết Black-Scholes")
    st.plotly_chart(create_backtest_price_chart(df, selected_bt), use_container_width=True)
    chart_container_end()

    # Chart P/D %
    if "premium_discount_pct" in df.columns:
        chart_container("Premium / Discount % Theo Ngày")
        fig_pd = create_backtest_pd_chart(df, selected_bt)
        if fig_pd is not None:
            st.plotly_chart(fig_pd, use_container_width=True)
        chart_container_end()

    # Bảng chi tiết
    section_divider()
    with st.expander("Xem Dữ Liệu Chi Tiết"):
        display_cols = {
            "Ngày": df["date"].dt.strftime("%d/%m/%Y"),
            "Giá CS (S)": df["S"].map(lambda x: f"{x:,.0f} đ") if "S" in df.columns else "N/A",
            "Giá TT (đ)": df["cw_price"].map(lambda x: f"{x:,.2f}"),
            "Giá LT (đ)": df["theoretical_price"].map(lambda x: f"{x:,.2f}"),
            "Sai Lệch (đ)": (df["cw_price"] - df["theoretical_price"]).map(lambda x: f"{x:+,.2f}"),
        }
        if "premium_discount_pct" in df.columns:
            display_cols["P/D %"] = df["premium_discount_pct"].map(lambda x: f"{x:+.2f}%")
        if "delta" in df.columns:
            display_cols["Delta"] = df["delta"].map(
                lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")
        if "sigma" in df.columns:
            display_cols["Sigma (σ)"] = df["sigma"].map(
                lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
        table_container("Dữ Liệu Lịch Sử", badge=f"{len(df)} ngày")
        render_table(pd.DataFrame(display_cols))
        table_container_end()
