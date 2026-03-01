"""
Tab: Phòng Ngừa Rủi Ro CW của TCPH (Tổ Chức Phát Hành).

Công thức theo quy định CW Việt Nam:
    P_T = |Δ_raw| × OI_T / k   — Vị thế lý thuyết bắt buộc
    ΔpT% = (P_T − p_T) / P_T × 100  — Độ lệch thực tế vs lý thuyết
    Hệ thống đèn 3 màu: 🟢 ≤ green_thr% | 🟡 ≤ yellow_thr% | 🔴 > yellow_thr%
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from ui.components import (
    format_vnd, section_title, colored_metric,
    tab_empty_state, chart_container, chart_container_end,
    section_divider, table_container, table_container_end, render_table,
)
from ui.charts import (
    COLORS,
    create_issuer_hedge_chart,
    create_issuer_forecast_chart,
)
from data.issuer_hedging_tracker import (
    save_hedge_record,
    load_hedge_history,
    get_all_tracked_cw_hedge,
    get_hedge_dataframe,
    export_hedge_csv,
    delete_hedge_record,
    delete_all_hedge_history,
    compute_hedge_fields,
)
from core.issuer_hedging import (
    get_compliance_status,
    forecast_hedge_positions,
)


# ─────────────────────────────────────────────────────────────────
# Session state key prefix
# ─────────────────────────────────────────────────────────────────
_HT = "_ht_"


def _k(suffix: str) -> str:
    return f"{_HT}{suffix}"


# ─────────────────────────────────────────────────────────────────
# Helper: CW options & static data
# ─────────────────────────────────────────────────────────────────

def _build_ht_cw_options() -> list:
    """Returns list of (label, ma_cw) — portfolio CW first, then history-only."""
    portfolio = st.session_state.get("cw_portfolio", [])
    tracked   = set(get_all_tracked_cw_hedge())
    options   = []
    seen      = set()

    for cw in portfolio:
        ma    = cw.get("ma_cw", "N/A").upper()
        cs    = cw.get("ma_co_so", "N/A").upper()
        loai  = "CALL" if cw.get("option_type") == "call" else "PUT"
        options.append((f"{ma} | {cs} | {loai}", ma))
        seen.add(ma)

    for ma in sorted(tracked):
        if ma not in seen:
            options.append((f"{ma} (chỉ có lịch sử hedge)", ma))

    return options


def _get_ht_cw_static(ma_cw: str) -> dict:
    """Lấy CW static params từ portfolio; fallback sang JSON history file."""
    portfolio = st.session_state.get("cw_portfolio", [])
    for cw in portfolio:
        if cw.get("ma_cw", "").upper() == ma_cw.upper():
            mat = cw.get("maturity_date", "")
            if isinstance(mat, date):
                mat = mat.strftime("%d/%m/%Y")
            return {
                "K":            cw.get("K", 0),
                "cr":           cw.get("cr", 1),
                "option_type":  cw.get("option_type", "call"),
                "maturity_date": mat,
                "r":            cw.get("r", 0.03),
                "q":            cw.get("q", 0.0),
                "ma_co_so":     cw.get("ma_co_so", "N/A"),
                "sigma":        cw.get("sigma", 0.30),
            }

    # Fallback: đọc từ JSON history
    data = load_hedge_history(ma_cw)
    if data:
        return {
            "K":            data.get("K", 0),
            "cr":           data.get("cr", 1),
            "option_type":  data.get("option_type", "call"),
            "maturity_date": data.get("maturity_date", ""),
            "r":            data.get("r", 0.03),
            "q":            data.get("q", 0.0),
            "ma_co_so":     data.get("ma_co_so", "N/A"),
            "sigma":        0.30,
        }
    return {}


def _parse_num(text: str) -> float:
    """Parse số từ text có thể chứa dấu phẩy."""
    try:
        return float(str(text).replace(",", "").replace(" ", "").strip())
    except (ValueError, TypeError):
        return 0.0


# ─────────────────────────────────────────────────────────────────
# Helper: status badge HTML
# ─────────────────────────────────────────────────────────────────

_STATUS_CFG = {
    "safe":    ("🟢", "An Toàn",            "#22C55E", "rgba(34,197,94,0.12)"),
    "warning": ("🟡", "Cảnh Báo",           "#F59E0B", "rgba(245,158,11,0.12)"),
    "danger":  ("🔴", "Cần Tái Cân Bằng",   "#EF4444", "rgba(239,68,68,0.12)"),
    "error":   ("⚠",  "Lỗi Tính Toán",      "#94A3B8", "rgba(148,163,184,0.10)"),
}


def _badge(status: str) -> str:
    icon, label, color, bg = _STATUS_CFG.get(status, _STATUS_CFG["error"])
    return (
        f'<span style="background:{bg};border:1px solid {color}55;'
        f'border-radius:6px;padding:5px 14px;font-size:0.9rem;'
        f'color:{color};font-weight:700;">{icon} {label}</span>'
    )


# ─────────────────────────────────────────────────────────────────
# Section 2 helpers: form + CSV upload
# ─────────────────────────────────────────────────────────────────

def _handle_form_submit(
    ma_cw, cw_static,
    date_raw, oi_str, p_actual_str,
    use_S: float, use_sigma_pct: float,
    green_thr, yellow_thr,
):
    """Parse, validate, compute, save và hiển thị kết quả form submit.

    Args:
        use_S        : Giá cổ phiếu cơ sở (float, từ lần nhập trước / override).
        use_sigma_pct: Biến động % (VD: 35.0), đã là số thực.
    """
    # Parse date (nhiều format)
    input_date = None
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            input_date = datetime.strptime(date_raw.strip(), fmt).date()
            break
        except ValueError:
            continue

    oi       = int(_parse_num(oi_str))
    p_actual = _parse_num(p_actual_str)

    # Validation
    errors = []
    if input_date is None:
        errors.append("Định dạng ngày không hợp lệ — dùng DD/MM/YY")
    if use_S <= 0:
        errors.append("Giá cơ sở S chưa được thiết lập — vui lòng nhập S ở ô bên dưới")
    if use_sigma_pct <= 0:
        errors.append("Biến động σ phải > 0")
    if oi <= 0:
        errors.append("OI (số CW lưu hành) phải > 0")
    if errors:
        for e in errors:
            st.error(f"× {e}")
        return

    record_input = {
        "date":     input_date.strftime("%Y-%m-%d"),
        "S":        use_S,
        "sigma":    use_sigma_pct / 100.0,
        "oi":       oi,
        "p_actual": p_actual,
    }

    auto = compute_hedge_fields(cw_static, record_input)
    # Override status với custom threshold từ UI
    if auto.get("deviation_pct") is not None:
        auto["status"] = get_compliance_status(
            auto["deviation_pct"], green_thr, yellow_thr
        )

    record = {**record_input, **auto}
    save_hedge_record(ma_cw, cw_static, record)

    p_theo   = auto.get("p_theo")
    dev_pct  = auto.get("deviation_pct")
    status   = auto.get("status", "error")
    buy_sell = auto.get("buy_sell", 0)

    # Hiển thị kết quả
    msg = f"✓ Đã lưu **{input_date.strftime('%d/%m/%Y')}** — **{ma_cw}**"
    if p_theo  is not None: msg += f" | P_T: **{p_theo:,.0f} CP**"
    if dev_pct is not None: msg += f" | ΔpT: **{dev_pct:+.2f}%**"

    if status == "safe":
        st.success(msg)
    elif status == "warning":
        st.warning(msg + " | ⚠ Lên kế hoạch tái cân bằng")
    elif status == "danger":
        st.error(msg + f" | 🔴 CẦN TÁI CÂN BẰNG NGAY ({abs(buy_sell):,} CP)")
    else:
        st.info(msg)

    st.markdown(_badge(status), unsafe_allow_html=True)


def _render_csv_upload(ma_cw, cw_static, green_thr, yellow_thr,
                       fallback_S: float = 0.0, fallback_sigma_pct: float = 30.0):
    """Bulk import dữ liệu từ CSV.

    Cột bắt buộc: date, oi, p_actual.
    Cột tùy chọn: S, sigma_pct — nếu thiếu sẽ dùng giá trị fallback.
    """
    st.markdown(
        '<div class="info-box">'
        'Cột bắt buộc: <b>date, oi, p_actual</b><br>'
        'Cột tùy chọn: <b>S, sigma_pct</b> — nếu không có sẽ dùng giá CS và σ hiện tại.<br>'
        'Định dạng ngày: <b>DD/MM/YYYY</b> hoặc <b>YYYY-MM-DD</b>. '
        'sigma_pct tính theo % (VD: 35.0 = 35%). '
        'sigma_pct &lt; 1 được tự động nhân 100 (decimal format).'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Chọn file CSV",
        type=["csv"],
        key=_k("csv_upload"),
    )
    if uploaded is None:
        return

    try:
        df_csv = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Lỗi đọc CSV: {e}")
        return

    required = ["date", "oi", "p_actual"]
    missing  = [c for c in required if c not in df_csv.columns]
    if missing:
        st.error(f"Thiếu cột bắt buộc: {', '.join(missing)}")
        return

    ok_cnt = err_cnt = 0
    for _, row in df_csv.iterrows():
        try:
            date_raw = str(row["date"]).strip()
            parsed   = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
                try:
                    parsed = datetime.strptime(date_raw, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed is None:
                err_cnt += 1
                continue

            # S: từ CSV nếu có, không thì dùng fallback
            if "S" in df_csv.columns and not pd.isna(row.get("S", None)):
                row_S = float(row["S"])
            else:
                row_S = fallback_S

            # sigma: từ CSV nếu có, không thì dùng fallback (%)
            if "sigma_pct" in df_csv.columns and not pd.isna(row.get("sigma_pct", None)):
                sig = float(row["sigma_pct"])
                if sig > 1:
                    sig = sig / 100.0   # normalize %→decimal
            else:
                sig = fallback_sigma_pct / 100.0

            if row_S <= 0 or sig <= 0:
                err_cnt += 1
                continue

            rec_in = {
                "date":     parsed.strftime("%Y-%m-%d"),
                "S":        row_S,
                "sigma":    sig,
                "oi":       int(float(row["oi"])),
                "p_actual": float(row["p_actual"]),
            }
            auto = compute_hedge_fields(cw_static, rec_in)
            if auto.get("deviation_pct") is not None:
                auto["status"] = get_compliance_status(
                    auto["deviation_pct"], green_thr, yellow_thr
                )
            save_hedge_record(ma_cw, cw_static, {**rec_in, **auto})
            ok_cnt += 1
        except Exception:
            err_cnt += 1

    result = f"✓ Import: **{ok_cnt}** records thành công"
    if err_cnt:
        result += f", **{err_cnt}** lỗi (kiểm tra S > 0 và ngày hợp lệ)"
    st.success(result)
    if ok_cnt:
        st.rerun()


# ─────────────────────────────────────────────────────────────────
# Section 3: Dashboard vị thế hiện tại
# ─────────────────────────────────────────────────────────────────

def _render_current_dashboard(records: list, green_thr: float, yellow_thr: float):
    section_title("◈", "Vị Thế Phòng Ngừa Hiện Tại")

    last     = records[-1]
    p_theo   = last.get("p_theo")
    p_actual = last.get("p_actual")
    dev_pct  = last.get("deviation_pct")
    delta_r  = last.get("delta_raw")
    buy_sell = last.get("buy_sell", 0)
    oi       = last.get("oi", 0)
    last_dt  = last.get("date", "")

    # Recompute status với custom threshold (live, không re-save)
    status = get_compliance_status(dev_pct, green_thr, yellow_thr) \
        if dev_pct is not None else "error"

    # ── 4 metric cards ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        colored_metric(
            "P_T Lý Thuyết",
            f"{p_theo:,.0f} CP" if p_theo is not None else "N/A",
            COLORS["secondary"],
            delta=f"OI = {oi:,} CW",
        )
    with c2:
        act_color = "#22C55E" if (p_actual or 0) >= (p_theo or 0) else COLORS["negative"]
        colored_metric(
            "p_T Thực Tế",
            f"{p_actual:,.0f} CP" if p_actual is not None else "N/A",
            act_color,
        )
    with c3:
        dev_color = ("#22C55E" if status == "safe"
                     else "#F59E0B" if status == "warning"
                     else "#EF4444")
        colored_metric(
            "ΔpT%  (P_T − p_T)/P_T",
            f"{dev_pct:+.2f}%" if dev_pct is not None else "N/A",
            dev_color,
        )
    with c4:
        colored_metric(
            "Delta (raw Δ)",
            f"{delta_r:.4f}" if delta_r is not None else "N/A",
            COLORS["accent"],
            delta=f"Ngày {last_dt}",
        )

    # ── Status badge + message ───────────────────────────────────
    st.markdown("")
    st.markdown(_badge(status), unsafe_allow_html=True)

    msgs = {
        "safe":    f"Vị thế hedge trong ngưỡng an toàn (|ΔpT%| ≤ {green_thr:.0f}%). Không cần hành động.",
        "warning": (f"Độ lệch vượt ngưỡng {green_thr:.0f}% nhưng chưa đến {yellow_thr:.0f}%. "
                    "Lên kế hoạch tái cân bằng trong thời gian sắp tới."),
        "danger":  (f"Độ lệch vượt ngưỡng {yellow_thr:.0f}%. "
                    "CẦN TÁI CÂN BẰNG NGAY ĐỂ TUÂN THỦ QUY ĐỊNH UBCKNN!"),
        "error":   "Lỗi tính toán. Kiểm tra lại tham số đầu vào.",
    }
    st.caption(msgs.get(status, ""))

    # ── Tín hiệu giao dịch ──────────────────────────────────────
    if buy_sell is not None and buy_sell != 0:
        direction = "MUA THÊM" if buy_sell > 0 else "BÁN BỚT"
        dir_color = "#22C55E" if buy_sell > 0 else COLORS["negative"]
        dir_icon  = "▲" if buy_sell > 0 else "▼"
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.04);border-radius:10px;'
            f'padding:12px 18px;margin-top:10px;border-left:3px solid {dir_color};">'
            f'<span style="color:#8896AB;font-size:0.75rem;">TÍN HIỆU TÁI CÂN BẰNG</span><br>'
            f'<span style="color:{dir_color};font-size:1.15rem;font-weight:700;">'
            f'{dir_icon} {direction} {abs(buy_sell):,} CP</span>'
            f'<span style="color:#8896AB;font-size:0.8rem;margin-left:12px;">'
            f'để đưa p_T → P_T</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────
# Section 4: Biểu đồ lịch sử + bảng
# ─────────────────────────────────────────────────────────────────

def _render_history_section(ma_cw: str, records: list, green_thr: float, yellow_thr: float):
    section_title("△", "Lịch Sử Vị Thế Hedge")

    if len(records) >= 2:
        df = get_hedge_dataframe(ma_cw)
        if df is not None and not df.empty:
            chart_container("P_T Lý Thuyết vs p_T Thực Tế & ΔpT%")
            st.plotly_chart(
                create_issuer_hedge_chart(df),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            chart_container_end()
    else:
        st.caption("Cần ít nhất 2 ngày dữ liệu để hiển thị biểu đồ.")

    # ── Bảng dữ liệu ──────────────────────────────────────────
    rows = []
    for r in reversed(records):
        dev  = r.get("deviation_pct")
        stat = get_compliance_status(dev, green_thr, yellow_thr) \
            if dev is not None else r.get("status", "error")
        stat_label = {
            "safe":    "🟢 An Toàn",
            "warning": "🟡 Cảnh Báo",
            "danger":  "🔴 Cần Cân Bằng",
            "error":   "⚠ Lỗi",
        }.get(stat, "⚠ Lỗi")

        bs = r.get("buy_sell")
        rows.append({
            "Ngày":      datetime.strptime(r["date"], "%Y-%m-%d").strftime("%d/%m/%Y"),
            "OI (CW)":   f"{r.get('oi', 0):,}",
            "S (đ)":     format_vnd(r.get("S", 0)),
            "σ (%)":     f"{r.get('sigma', 0)*100:.1f}%",
            "Δ raw":     f"{r.get('delta_raw', 0):.4f}" if r.get("delta_raw") is not None else "N/A",
            "P_T (CP)":  f"{r.get('p_theo', 0):,.0f}"   if r.get("p_theo")    is not None else "N/A",
            "p_T (CP)":  f"{r.get('p_actual', 0):,.0f}",
            "ΔpT%":      f"{dev:+.2f}%"                  if dev  is not None else "N/A",
            "Mua/Bán":   f"{bs:+,}"                       if bs   is not None else "N/A",
            "Trạng Thái": stat_label,
        })

    section_divider()
    table_container("Lịch Sử Dữ Liệu Hedge", badge=f"{len(records)} ngày")
    render_table(pd.DataFrame(rows))
    table_container_end()

    # Export CSV
    csv_str = export_hedge_csv(ma_cw)
    if csv_str:
        st.download_button(
            label="↓ Tải Lịch Sử CSV",
            data=csv_str.encode("utf-8"),
            file_name=f"hedge_{ma_cw.upper()}.csv",
            mime="text/csv",
            key=_k("export_csv"),
        )


# ─────────────────────────────────────────────────────────────────
# Section 5: Dự báo 30 ngày
# ─────────────────────────────────────────────────────────────────

def _render_forecast_section(ma_cw, cw_static, records, green_thr, yellow_thr):
    section_title("▹", "Dự Báo Vị Thế Bắt Buộc (30 Ngày Tới)")

    last      = records[-1]
    last_S    = last.get("S", 0)
    last_sig  = last.get("sigma", cw_static.get("sigma", 0.30))
    last_oi   = last.get("oi", 0)
    last_pact = last.get("p_actual", 0)
    last_date = last.get("date", date.today().strftime("%Y-%m-%d"))
    mat_str   = cw_static.get("maturity_date", "")

    if last_S <= 0 or last_sig <= 0 or last_oi <= 0:
        st.caption("Thiếu dữ liệu hợp lệ (S, σ, OI) để dự báo.")
        return
    if not mat_str:
        st.caption("Không có ngày đáo hạn — không thể dự báo.")
        return

    st.markdown(
        '<div class="info-box">'
        'Dự báo giả định <b>OI và σ cố định</b>, chỉ T thay đổi mỗi ngày. '
        'P_T giảm dần khi Δ tiến về 0 (theta decay gần đáo hạn). '
        'Kết quả cho thấy TCPH cần nắm giữ bao nhiêu CP mỗi ngày tới.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Cho phép override tham số giả định
    with st.expander("⚙ Tùy Chỉnh Tham Số Dự Báo", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            fc_S = st.number_input(
                "Giá CS giả định (S)",
                value=float(last_S), min_value=0.0, step=1000.0,
                format="%.0f", key=_k("fc_S"),
            )
        with fc2:
            fc_sig_pct = st.number_input(
                "σ giả định (%)",
                value=float(last_sig * 100), min_value=0.1, max_value=300.0,
                step=0.5, key=_k("fc_sigma"),
            )
        with fc3:
            fc_oi = st.number_input(
                "OI giả định (CW)",
                value=int(last_oi), min_value=1, step=10000,
                key=_k("fc_oi"),
            )

    # Lấy giá trị từ session state (đã được widget set)
    use_S   = st.session_state.get(_k("fc_S"),     last_S)
    use_sig = st.session_state.get(_k("fc_sigma"), last_sig * 100) / 100.0
    use_oi  = int(st.session_state.get(_k("fc_oi"), last_oi))

    forecast = forecast_hedge_positions(
        S               = use_S,
        K               = cw_static["K"],
        r               = cw_static.get("r",  0.03),
        sigma           = use_sig,
        q               = cw_static.get("q",  0.0),
        option_type     = cw_static.get("option_type", "call"),
        cr              = cw_static["cr"],
        oi              = use_oi,
        maturity_date_str = mat_str,
        from_date_str   = last_date,
        days_ahead      = 30,
    )

    if not forecast:
        st.caption("CW đã đáo hạn hoặc không đủ dữ liệu để dự báo.")
        return

    # ── Tóm tắt dự báo: T+1, T+7, T+30 ─────────────────────────
    def _fc_val(idx):
        if idx < len(forecast):
            return forecast[idx]
        return forecast[-1]

    m1, m2, m3 = st.columns(3)
    pts = [("T+1", 0), ("T+7", 6), ("T+30", 29)]
    for col, (label, idx) in zip([m1, m2, m3], pts):
        fd = _fc_val(idx)
        pt = fd.get("p_theo")
        with col:
            colored_metric(
                label,
                f"{pt:,.0f} CP" if pt is not None else "N/A",
                COLORS["accent"],
                delta=f"Δ = {fd.get('delta_raw', 0):.4f}" if fd.get("delta_raw") else None,
            )

    # ── Chart ────────────────────────────────────────────────────
    chart_container("Dự Báo P_T — Delta Decay")
    st.plotly_chart(
        create_issuer_forecast_chart(forecast, last_pact, green_thr, yellow_thr),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    chart_container_end()

    # ── Bảng chi tiết ────────────────────────────────────────────
    with st.expander("Xem Bảng Dự Báo Chi Tiết"):
        fc_rows = []
        for fd in forecast:
            pt  = fd.get("p_theo")
            dr  = fd.get("delta_raw")
            dev = None
            if pt is not None:
                from core.issuer_hedging import compute_deviation
                dev = compute_deviation(pt, last_pact)
            stat = get_compliance_status(dev, green_thr, yellow_thr) if dev is not None else "error"
            stat_label = {
                "safe": "🟢", "warning": "🟡", "danger": "🔴", "error": "⚠",
            }.get(stat, "⚠")
            fc_rows.append({
                "Ngày":          datetime.strptime(fd["date"], "%Y-%m-%d").strftime("%d/%m/%Y"),
                "T Còn Lại":     f"{fd.get('days_to_maturity', 0)} ngày",
                "Δ raw":         f"{dr:.4f}" if dr is not None else "N/A",
                "P_T Dự Báo":    f"{pt:,.0f} CP" if pt is not None else "N/A",
                "Nếu giữ nguyên p_T": f"{dev:+.2f}%" if dev is not None else "N/A",
                "Trạng Thái":    stat_label,
            })
        table_container("Bảng Dự Báo Vị Thế", badge=f"{len(forecast)} ngày")
        render_table(pd.DataFrame(fc_rows))
        table_container_end()

    st.caption(
        f"Giả định: OI = {use_oi:,} CW | σ = {use_sig*100:.1f}% | S = {use_S:,.0f}đ. "
        "P_T thay đổi do Delta giảm khi T tiến về 0 (CW gần đáo hạn)."
    )


# ─────────────────────────────────────────────────────────────────
# Data management
# ─────────────────────────────────────────────────────────────────

def _render_data_management(ma_cw: str, records: list):
    section_title("⚙", "Quản Lý Dữ Liệu")

    col_del, col_all = st.columns(2)

    with col_del:
        if records:
            date_labels = [
                datetime.strptime(r["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
                for r in reversed(records)
            ]
            date_vals = [r["date"] for r in reversed(records)]
            del_idx = st.selectbox(
                "Chọn ngày cần xóa",
                range(len(date_labels)),
                format_func=lambda i: date_labels[i],
                key=_k("del_date"),
            )
            if st.button("× Xóa Ngày Này", key=_k("del_btn")):
                if delete_hedge_record(ma_cw, date_vals[del_idx]):
                    st.success("Đã xóa record.")
                    st.rerun()
                else:
                    st.error("Không thể xóa.")

    with col_all:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("△ Xóa Toàn Bộ Lịch Sử", key=_k("del_all"), type="secondary"):
            st.session_state[_k("confirm_del")] = True

        if st.session_state.get(_k("confirm_del")):
            st.warning(f"Xóa **{len(records)} ngày** dữ liệu của **{ma_cw}**?")
            cy, cn = st.columns(2)
            with cy:
                if st.button("✓ Xác Nhận Xóa", key=_k("confirm_yes")):
                    delete_all_hedge_history(ma_cw)
                    st.session_state.pop(_k("confirm_del"), None)
                    st.rerun()
            with cn:
                if st.button("× Hủy", key=_k("confirm_no")):
                    st.session_state.pop(_k("confirm_del"), None)
                    st.rerun()


# ─────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────

def render_issuer_hedging_tab():
    """Tab 12: Phòng Ngừa Rủi Ro CW của TCPH."""
    section_title("⊛", "Phòng Ngừa Rủi Ro CW của TCPH")

    st.markdown(
        '<div class="info-box">'
        'Theo dõi và kiểm soát vị thế phòng ngừa rủi ro của '
        '<b>Tổ Chức Phát Hành (TCPH)</b> theo quy định UBCKNN.<br>'
        '&bull; <b>P_T = |Δ| × OI / k</b> — Số CP lý thuyết TCPH bắt buộc nắm giữ<br>'
        '&bull; <b>ΔpT% = (P_T − p_T) / P_T × 100</b> — Độ lệch thực tế<br>'
        '&bull; Cảnh báo 3 mức: 🟢 An toàn &nbsp;|&nbsp; '
        '🟡 Cảnh báo &nbsp;|&nbsp; 🔴 Cần tái cân bằng ngay'
        '</div>',
        unsafe_allow_html=True,
    )

    # ════════════════════════════════════════════════════════
    # SECTION 1: CW SELECTOR + CẤU HÌNH
    # ════════════════════════════════════════════════════════
    cw_options = _build_ht_cw_options()

    if not cw_options:
        tab_empty_state(
            "⊛",
            "Chưa Có CW Nào Trong Portfolio",
            "Thêm CW vào portfolio ở Sidebar trước, sau đó quay lại đây.",
            "Sidebar → Thêm CW hoặc Import CSV",
        )
        return

    labels = [o[0] for o in cw_options]
    sel_idx = st.selectbox(
        "Chọn CW để theo dõi hedge của TCPH",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=_k("cw_selector"),
    )
    _, sel_ma = cw_options[sel_idx]
    cw_static = _get_ht_cw_static(sel_ma)

    if not cw_static:
        st.warning(f"Không tìm thấy thông tin tham số cho **{sel_ma}**.")
        return

    # Info bar
    st.markdown(
        f'<div style="font-size:0.8rem;color:#94A3B8;margin-bottom:10px;">'
        f'Mã CS: <b style="color:#F1F5F9;">{cw_static.get("ma_co_so","N/A")}</b> &nbsp;|&nbsp; '
        f'Strike K: <b style="color:#F1F5F9;">{format_vnd(cw_static.get("K",0))} đ</b> &nbsp;|&nbsp; '
        f'Loại: <b style="color:#F1F5F9;">{cw_static.get("option_type","call").upper()}</b> &nbsp;|&nbsp; '
        f'CR (k): <b style="color:#F1F5F9;">{cw_static.get("cr",1)}</b> &nbsp;|&nbsp; '
        f'Đáo hạn: <b style="color:#F1F5F9;">{cw_static.get("maturity_date","N/A")}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Cấu hình ngưỡng tuân thủ
    with st.expander("⚙ Cấu Hình Ngưỡng Tuân Thủ", expanded=False):
        cg, cy = st.columns(2)
        with cg:
            green_thr = st.slider(
                "Ngưỡng An Toàn 🟢 (%)",
                min_value=1, max_value=30,
                value=st.session_state.get(_k("green_thr"), 10),
                key=_k("green_thr"),
                help="Nếu |ΔpT%| ≤ ngưỡng này → An Toàn (xanh)",
            )
        with cy:
            yellow_thr = st.slider(
                "Ngưỡng Cảnh Báo 🟡 (%)",
                min_value=green_thr + 1, max_value=50,
                value=max(st.session_state.get(_k("yellow_thr"), 20), green_thr + 1),
                key=_k("yellow_thr"),
                help="Nếu ngưỡng xanh < |ΔpT%| ≤ ngưỡng này → Cảnh Báo (vàng)",
            )

    section_divider(thick=True)

    # ════════════════════════════════════════════════════════
    # SECTION 2: NHẬP DỮ LIỆU HÀNG NGÀY
    # ════════════════════════════════════════════════════════
    section_title("▹", "Nhập Dữ Liệu Hàng Ngày")

    st.markdown(
        '<div class="info-box">'
        '&bull; <b>OI</b>: Số lượng CW đang lưu hành tại ngày đó (tra trên HoSE/HNX)<br>'
        '&bull; <b>p_T</b>: Số CP cơ sở TCPH đang thực sự nắm giữ (báo cáo nội bộ/công bố)<br>'
        '&bull; App tự động dùng <b>Giá CS (S)</b> và <b>σ</b> từ lần nhập trước (hoặc portfolio) '
        'để tính Delta và P_T — cập nhật trong ô bên dưới nếu có thay đổi'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Xác định giá trị S và sigma mặc định ─────────────────────────
    # Ưu tiên: lần nhập trước (last record) → portfolio → 0
    _hist_now   = load_hedge_history(sel_ma)
    _prev_recs  = _hist_now.get("records", []) if _hist_now else []
    _last_rec   = _prev_recs[-1] if _prev_recs else None

    _default_S         = float(_last_rec.get("S", 0.0))       if _last_rec else 0.0
    _default_sigma_pct = cw_static.get("sigma", 0.30) * 100.0  # luôn dùng portfolio làm gốc

    # Khởi tạo session state cho S và sigma override
    if _k("use_S") not in st.session_state:
        st.session_state[_k("use_S")] = _default_S
    if _k("use_sigma_pct") not in st.session_state:
        st.session_state[_k("use_sigma_pct")] = _default_sigma_pct

    _cur_S       = st.session_state[_k("use_S")]
    _cur_sig_pct = st.session_state[_k("use_sigma_pct")]

    # ── Hiển thị giá trị đang dùng ───────────────────────────────────
    _s_src   = "lần nhập trước" if _last_rec and _default_S > 0 else "chưa có — nhập bên dưới"
    _sig_src = "portfolio"
    _s_color = "#94A3B8" if _cur_S > 0 else "#EF4444"
    st.markdown(
        f'<div style="font-size:0.78rem;color:#94A3B8;margin-bottom:6px;">'
        f'Đang dùng: '
        f'<b style="color:{_s_color};">S = {_cur_S:,.0f} đ</b> ({_s_src}) &nbsp;|&nbsp; '
        f'<b style="color:#94A3B8;">σ = {_cur_sig_pct:.1f}%</b> ({_sig_src})'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Expander cập nhật S và sigma ─────────────────────────────────
    with st.expander("✏ Cập Nhật Giá CS (S) & Biến Động (σ) nếu thay đổi", expanded=(_cur_S <= 0)):
        ov1, ov2, ov3 = st.columns([2, 2, 1])
        with ov1:
            _new_S = st.number_input(
                "Giá CS hiện tại (S)",
                value=max(float(_cur_S), 0.0),
                min_value=0.0, step=1_000.0, format="%.0f",
                help="Giá thị trường cổ phiếu cơ sở hôm nay — VD: 100,000",
                key=_k("inp_S"),
            )
        with ov2:
            _new_sig = st.number_input(
                "Biến động σ (%)",
                value=max(float(_cur_sig_pct), 0.1),
                min_value=0.1, max_value=300.0, step=0.5,
                help="Biến động ngầm định — VD: 35.0 = 35%",
                key=_k("inp_sigma"),
            )
        with ov3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Lưu", key=_k("ov_update"), use_container_width=True):
                st.session_state[_k("use_S")]        = _new_S
                st.session_state[_k("use_sigma_pct")] = _new_sig
                st.rerun()

    # ── Form chính: chỉ nhập OI và p_T ──────────────────────────────
    with st.form(key=_k("daily_form"), clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_date = st.text_input(
                "⊡ Ngày",
                value=date.today().strftime("%d/%m/%y"),
                help="DD/MM/YY — VD: 01/03/26",
            )
        with c2:
            f_oi = st.text_input(
                "OI (số CW lưu hành)",
                value="0",
                help="Số CW đang lưu hành tại ngày này — VD: 1,000,000",
            )
        with c3:
            f_pact = st.text_input(
                "p_T (CP TCPH đang nắm giữ)",
                value="0",
                help="Số CP cơ sở TCPH thực sự đang nắm giữ — VD: 500,000",
            )

        submitted = st.form_submit_button("▪ Tính & Lưu", use_container_width=True, type="primary")

    if submitted:
        _handle_form_submit(
            sel_ma, cw_static,
            f_date, f_oi, f_pact,
            st.session_state.get(_k("use_S"),        _default_S),
            st.session_state.get(_k("use_sigma_pct"), _default_sigma_pct),
            green_thr, yellow_thr,
        )

    # CSV bulk import
    section_divider()
    with st.expander("↑ Nhập Hàng Loạt (Upload CSV)", expanded=False):
        _render_csv_upload(
            sel_ma, cw_static, green_thr, yellow_thr,
            fallback_S=st.session_state.get(_k("use_S"), _default_S),
            fallback_sigma_pct=st.session_state.get(_k("use_sigma_pct"), _default_sigma_pct),
        )

    section_divider()

    # ════════════════════════════════════════════════════════
    # Load history — gating sections 3-5
    # ════════════════════════════════════════════════════════
    hist = load_hedge_history(sel_ma)
    records = hist.get("records", []) if hist else []

    if not records:
        tab_empty_state(
            "⊛",
            "Chưa Có Dữ Liệu Lịch Sử Hedge",
            f"Nhập dữ liệu cho **{sel_ma}** ở form bên trên.",
            "Cập nhật S & σ (nếu cần) → Nhập Ngày, OI, p_T → Tính & Lưu",
        )
        return

    # ════════════════════════════════════════════════════════
    # SECTION 3: DASHBOARD VỊ THẾ HIỆN TẠI
    # ════════════════════════════════════════════════════════
    _render_current_dashboard(records, green_thr, yellow_thr)

    section_divider()

    # ════════════════════════════════════════════════════════
    # SECTION 4: BIỂU ĐỒ LỊCH SỬ + BẢNG
    # ════════════════════════════════════════════════════════
    _render_history_section(sel_ma, records, green_thr, yellow_thr)

    section_divider()

    # ════════════════════════════════════════════════════════
    # SECTION 5: DỰ BÁO 30 NGÀY
    # ════════════════════════════════════════════════════════
    _render_forecast_section(sel_ma, cw_static, records, green_thr, yellow_thr)

    section_divider()

    # ════════════════════════════════════════════════════════
    # DATA MANAGEMENT
    # ════════════════════════════════════════════════════════
    _render_data_management(sel_ma, records)
