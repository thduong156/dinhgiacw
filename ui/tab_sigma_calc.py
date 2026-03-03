"""Tab: Tính Độ Lệch Chuẩn CKCS — tính Historical Volatility (σ) từ dữ liệu giá quá khứ."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import io

from ui.components import (
    section_title,
    colored_metric,
    section_divider,
    chart_container,
    chart_container_end,
    tab_empty_state,
)


# ── Hằng số ────────────────────────────────────────────────────────────────
TRADING_DAYS = 252  # số phiên giao dịch chuẩn trong 1 năm


# ── Tính toán ───────────────────────────────────────────────────────────────
def _calc_historical_vol(prices: list[float]) -> dict:
    """Tính Historical Volatility từ mảng giá đóng cửa."""
    arr = np.array(prices, dtype=float)
    log_returns = np.diff(np.log(arr))
    daily_sigma = float(np.std(log_returns, ddof=1))
    annual_sigma = daily_sigma * np.sqrt(TRADING_DAYS)
    mean_return = float(np.mean(log_returns))
    return {
        "annual_sigma": annual_sigma,
        "daily_sigma": daily_sigma,
        "mean_daily_return": mean_return,
        "n_prices": len(arr),
        "n_returns": len(log_returns),
        "log_returns": log_returns,
        "prices": arr,
    }


def _parse_text_prices(text: str) -> list[float] | None:
    """Parse chuỗi giá từ text (phân cách bằng dấu phẩy, xuống dòng hoặc tab)."""
    import re
    tokens = re.split(r"[,\n\r\t;]+", text.strip())
    prices = []
    for t in tokens:
        t = t.strip().replace(",", "").replace(".", ".", 1)
        if not t:
            continue
        try:
            prices.append(float(t))
        except ValueError:
            return None
    return prices if len(prices) >= 2 else None


# ── Chart giá ───────────────────────────────────────────────────────────────
def _chart_price(prices: np.ndarray, ticker: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=prices,
        mode="lines",
        line=dict(color="#4ECDC4", width=1.5),
        name="Giá đóng cửa",
        hovertemplate="Phiên %{x}<br>Giá: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Lịch Sử Giá — {ticker}", font=dict(size=13, color="#E8EAF0")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="#B8C2DB"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, title="Phiên"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)", title="Giá"),
        height=260,
    )
    return fig


# ── Chart phân phối log return ───────────────────────────────────────────────
def _chart_returns(log_returns: np.ndarray, daily_sigma: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=log_returns,
        nbinsx=40,
        marker_color="#FFE66D",
        opacity=0.8,
        name="Log Return",
        hovertemplate="Return: %{x:.4f}<br>Tần suất: %{y}<extra></extra>",
    ))
    # Đường chuẩn tham chiếu
    x_range = np.linspace(log_returns.min(), log_returns.max(), 200)
    mean = np.mean(log_returns)
    normal_curve = (
        np.exp(-0.5 * ((x_range - mean) / daily_sigma) ** 2)
        / (daily_sigma * np.sqrt(2 * np.pi))
        * len(log_returns)
        * (log_returns.max() - log_returns.min())
        / 40
    )
    fig.add_trace(go.Scatter(
        x=x_range, y=normal_curve,
        mode="lines",
        line=dict(color="#E74C3C", width=2, dash="dot"),
        name="Chuẩn tham chiếu",
    ))
    fig.update_layout(
        title=dict(text="Phân Phối Log Return Hàng Ngày", font=dict(size=13, color="#E8EAF0")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="#B8C2DB"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, title="Log Return"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)", title="Tần suất"),
        height=260,
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )
    return fig


# ── Hàm render chính ────────────────────────────────────────────────────────
def render_sigma_calc_tab():
    """Tab: Tính Độ Lệch Chuẩn CKCS (Historical Volatility)."""

    section_title("σ", "Tính Độ Lệch Chuẩn CKCS")

    st.markdown(
        "<p style='color:#8892A4;font-size:13px;margin-top:-8px;margin-bottom:16px;'>"
        "Tính <b>Historical Volatility (σ)</b> từ dữ liệu giá đóng cửa quá khứ — "
        "dùng làm đầu vào Volatility khi định giá CW.</p>",
        unsafe_allow_html=True,
    )

    # ── Nhập tên mã ─────────────────────────────────────────────────────────
    col_ticker, col_method, _ = st.columns([1, 1, 2])
    with col_ticker:
        ticker = st.text_input(
            "Mã chứng khoán cơ sở",
            value="",
            placeholder="VD: VNM, HPG, VIC...",
            key="sigma_ticker",
        ).strip().upper()
    with col_method:
        method = st.radio(
            "Nhập dữ liệu bằng",
            ["Nhập tay", "Upload CSV"],
            horizontal=True,
            key="sigma_input_method",
        )

    section_divider()

    prices_raw: list[float] | None = None

    # ── Nhập tay ────────────────────────────────────────────────────────────
    if method == "Nhập tay":
        st.markdown(
            "<p style='color:#8892A4;font-size:12px;margin-bottom:4px;'>"
            "Dán giá đóng cửa theo thứ tự cũ → mới. Phân cách bằng dấu phẩy, "
            "Enter hoặc Tab. Tối thiểu 2 giá trị.</p>",
            unsafe_allow_html=True,
        )
        raw_text = st.text_area(
            "Dán dữ liệu giá đóng cửa",
            height=160,
            placeholder="68500\n69200\n70100\n68900\n...",
            key="sigma_raw_text",
            label_visibility="collapsed",
        )
        if raw_text.strip():
            prices_raw = _parse_text_prices(raw_text)
            if prices_raw is None:
                st.error("Dữ liệu không hợp lệ. Chỉ nhập số, phân cách bằng dấu phẩy hoặc xuống dòng.")

    # ── Upload CSV ──────────────────────────────────────────────────────────
    else:
        st.markdown(
            "<p style='color:#8892A4;font-size:12px;margin-bottom:4px;'>"
            "File CSV cần có cột <b>Close</b> hoặc <b>close</b> (giá đóng cửa). "
            "Thứ tự hàng: cũ → mới.</p>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload file CSV",
            type=["csv"],
            key="sigma_csv_upload",
            label_visibility="collapsed",
        )
        if uploaded is not None:
            try:
                df_upload = pd.read_csv(io.StringIO(uploaded.read().decode("utf-8")))
                # Tìm cột giá
                close_col = None
                for c in df_upload.columns:
                    if c.strip().lower() in ("close", "close price", "gia dong cua", "giá đóng cửa", "price"):
                        close_col = c
                        break
                if close_col is None:
                    st.error(
                        f"Không tìm thấy cột 'Close' trong file. "
                        f"Các cột hiện có: {', '.join(df_upload.columns.tolist())}"
                    )
                else:
                    prices_raw = df_upload[close_col].dropna().astype(float).tolist()
                    if len(prices_raw) < 2:
                        st.error("File CSV có quá ít dữ liệu (cần ít nhất 2 dòng).")
                        prices_raw = None
                    else:
                        st.success(f"Đã đọc **{len(prices_raw)}** giá từ cột '{close_col}'.")
            except Exception as e:
                st.error(f"Lỗi đọc file CSV: {e}")

    # ── Tính toán & hiển thị kết quả ────────────────────────────────────────
    if prices_raw and len(prices_raw) >= 2:
        result = _calc_historical_vol(prices_raw)
        annual_pct = result["annual_sigma"] * 100
        daily_pct = result["daily_sigma"] * 100

        section_divider()
        display_name = ticker if ticker else "CKCS"

        # Kết quả nổi bật
        st.markdown(
            f"<div style='background:rgba(78,205,196,0.08);border:1px solid rgba(78,205,196,0.3);"
            f"border-radius:10px;padding:18px 24px;margin-bottom:16px;'>"
            f"<div style='color:#8892A4;font-size:12px;margin-bottom:4px;'>Volatility (σ) năm — dùng cho định giá CW</div>"
            f"<div style='color:#4ECDC4;font-size:36px;font-weight:700;letter-spacing:1px;'>"
            f"{annual_pct:.2f}%</div>"
            f"<div style='color:#8892A4;font-size:11px;margin-top:4px;'>"
            f"= {result['annual_sigma']:.4f} (dạng thập phân · nhập trực tiếp vào ô σ khi định giá)</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Metrics phụ
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            colored_metric("σ Ngày", f"{daily_pct:.4f}%", "#4ECDC4")
        with m2:
            colored_metric("σ Năm", f"{annual_pct:.2f}%", "#FFE66D")
        with m3:
            colored_metric("Số phiên dữ liệu", f"{result['n_prices']:,}", "#B8C2DB")
        with m4:
            sign = "+" if result["mean_daily_return"] >= 0 else ""
            colored_metric(
                "Return TB/ngày",
                f"{sign}{result['mean_daily_return']*100:.4f}%",
                "#2ECC71" if result["mean_daily_return"] >= 0 else "#E74C3C",
            )

        # Ghi chú phương pháp
        section_divider()
        st.markdown(
            "<details><summary style='color:#8892A4;font-size:12px;cursor:pointer;'>"
            "▶ Phương pháp tính</summary>"
            "<div style='color:#8892A4;font-size:12px;padding:8px 0;'>"
            "1. Tính <b>log return</b> hàng ngày: <code>r_t = ln(P_t / P_{t-1})</code><br>"
            f"2. Tính độ lệch chuẩn mẫu: <code>σ_ngày = std(r_t) = {daily_pct:.4f}%</code><br>"
            f"3. Quy đổi sang năm: <code>σ_năm = σ_ngày × √{TRADING_DAYS} = {annual_pct:.2f}%</code><br>"
            f"4. Số phiên tính: <b>{result['n_returns']}</b> log returns từ <b>{result['n_prices']}</b> giá"
            "</div></details>",
            unsafe_allow_html=True,
        )

        # Charts
        section_divider()
        c_left, c_right = st.columns(2)
        with c_left:
            chart_container(f"Lịch Sử Giá — {display_name}")
            fig_price = _chart_price(result["prices"], display_name)
            st.plotly_chart(fig_price, use_container_width=True)
            chart_container_end()
        with c_right:
            chart_container("Phân Phối Log Return")
            fig_ret = _chart_returns(result["log_returns"], result["daily_sigma"])
            st.plotly_chart(fig_ret, use_container_width=True)
            chart_container_end()

    elif prices_raw is not None and len(prices_raw) < 2:
        st.warning("Cần ít nhất 2 giá trị để tính độ lệch chuẩn.")
