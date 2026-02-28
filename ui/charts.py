import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator


CHART_TEMPLATE = "plotly_dark"
COLORS = {
    "primary": "#FF6B35",
    "secondary": "#4ECDC4",
    "accent": "#FFE66D",
    "positive": "#2ECC71",
    "negative": "#E74C3C",
    "neutral": "#95A5A6",
    "bg": "#0E1117",
    "grid": "rgba(255,255,255,0.05)",
    "purple": "#A78BFA",
    "blue": "#3B82F6",
}

CHART_FONT = dict(family="Fira Code, monospace", size=12, color="#CBD5E0")

COMMON_LAYOUT = dict(
    template=CHART_TEMPLATE,
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["bg"],
    font=CHART_FONT,
    margin=dict(l=50, r=30, t=50, b=50),
    hoverlabel=dict(
        bgcolor="#1A2332",
        font_size=13,
        font_family="Fira Code, monospace",
        bordercolor="rgba(255,107,53,0.3)",
    ),
)


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert hex color (#RRGGBB) to rgba() string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _apply_axis_style(fig, xaxis_title="", yaxis_title=""):
    """Áp dụng style trục thống nhất."""
    fig.update_xaxes(
        title_text=xaxis_title,
        gridcolor=COLORS["grid"],
        zeroline=False,
        title_font=dict(size=11, color="#8896AB"),
    )
    fig.update_yaxes(
        title_text=yaxis_title,
        gridcolor=COLORS["grid"],
        zeroline=False,
        title_font=dict(size=11, color="#8896AB"),
    )


def create_payoff_diagram(S, K, cw_price, cr, option_type, sigma, T, r):
    """Biểu đồ payoff tại đáo hạn + giá trị hiện tại."""
    S_range = np.linspace(S * 0.5, S * 1.5, 200)

    # Payoff tại đáo hạn
    if option_type == "call":
        payoff = np.maximum(S_range - K, 0) / cr - cw_price
        be = K + cw_price * cr
    else:
        payoff = np.maximum(K - S_range, 0) / cr - cw_price
        be = K - cw_price * cr

    # Giá trị hiện tại (theoretical)
    current_values = []
    for s in S_range:
        model = BlackScholesModel(s, K, T, r, sigma, option_type)
        current_values.append(model.price() / cr - cw_price)

    fig = go.Figure()

    # Vùng lãi/lỗ
    payoff_arr = np.array(payoff)
    fig.add_trace(go.Scatter(
        x=S_range, y=payoff,
        name="Lợi nhuận tại đáo hạn",
        line=dict(color=COLORS["primary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(255, 107, 53, 0.08)",
        hovertemplate="Giá CS: %{x:,.0f} đ<br>Lợi nhuận: %{y:,.0f} đ<extra>Đáo hạn</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=S_range, y=current_values,
        name="Giá trị hiện tại",
        line=dict(color=COLORS["secondary"], width=2, dash="dash"),
        hovertemplate="Giá CS: %{x:,.0f} đ<br>Giá trị: %{y:,.0f} đ<extra>Hiện tại</extra>",
    ))

    # Đường zero
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["neutral"], opacity=0.5)

    # Điểm hòa vốn
    fig.add_vline(x=be, line_dash="dash", line_color=COLORS["accent"],
                  annotation_text=f"Hoà vốn: {be:,.0f} đ",
                  annotation_position="top",
                  annotation_font=dict(size=11, color=COLORS["accent"]))

    # Giá hiện tại
    fig.add_vline(x=S, line_dash="dot", line_color=COLORS["positive"],
                  annotation_text=f"Giá hiện tại: {S:,.0f} đ",
                  annotation_position="bottom",
                  annotation_font=dict(size=11, color=COLORS["positive"]))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Biểu Đồ Lợi Nhuận (Payoff Diagram)", font=dict(size=14)),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)"),
        height=450,
    )
    _apply_axis_style(fig, "Giá Cổ Phiếu Cơ Sở (đ)", "Lợi Nhuận / Lỗ (đ)")

    return fig


def create_greeks_vs_price(S, K, T, r, sigma, cr, option_type, q=0.0):
    """Biểu đồ Delta và Gamma theo giá cơ sở."""
    S_range = np.linspace(S * 0.5, S * 1.5, 150)
    deltas = []
    gammas = []

    for s in S_range:
        model = BlackScholesModel(s, K, T, r, sigma, option_type, q=q)
        calc = GreeksCalculator(model, cr)
        deltas.append(calc.delta())
        gammas.append(calc.gamma())

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=S_range, y=deltas, name="Delta",
            line=dict(color=COLORS["primary"], width=2.5),
            hovertemplate="Giá CS: %{x:,.0f} đ<br>Delta: %{y:.4f}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=S_range, y=gammas, name="Gamma",
            line=dict(color=COLORS["secondary"], width=2.5),
            hovertemplate="Giá CS: %{x:,.0f} đ<br>Gamma: %{y:.6f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.add_vline(x=S, line_dash="dot", line_color=COLORS["accent"], opacity=0.6,
                  annotation_text=f"Hiện tại: {S:,.0f}",
                  annotation_font=dict(size=10, color=COLORS["accent"]))
    fig.add_vline(x=K, line_dash="dash", line_color=COLORS["neutral"], opacity=0.4,
                  annotation_text=f"Strike: {K:,.0f}",
                  annotation_font=dict(size=10, color=COLORS["neutral"]))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Delta & Gamma theo Giá Cơ Sở", font=dict(size=14)),
        height=400,
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)"),
    )
    fig.update_xaxes(title_text="Giá Cổ Phiếu Cơ Sở (đ)",
                     gridcolor=COLORS["grid"], title_font=dict(size=11, color="#8896AB"))
    fig.update_yaxes(title_text="Delta", secondary_y=False,
                     gridcolor=COLORS["grid"], title_font=dict(size=11, color=COLORS["primary"]))
    fig.update_yaxes(title_text="Gamma", secondary_y=True,
                     gridcolor=COLORS["grid"], title_font=dict(size=11, color=COLORS["secondary"]))

    return fig


def create_greeks_vs_time(S, K, T, r, sigma, cr, option_type, q=0.0):
    """Biểu đồ Greeks theo thời gian còn lại."""
    days = np.linspace(1, max(T * 365, 2), 100)
    T_range = days / 365.0

    deltas = []
    gammas = []
    thetas = []
    vegas = []

    for t in T_range:
        model = BlackScholesModel(S, K, t, r, sigma, option_type, q=q)
        calc = GreeksCalculator(model, cr)
        deltas.append(calc.delta())
        gammas.append(calc.gamma())
        thetas.append(calc.theta())
        vegas.append(calc.vega())

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Delta", "Gamma", "Theta (mỗi ngày)", "Vega"),
        vertical_spacing=0.15,
        horizontal_spacing=0.12,
    )

    colors = [COLORS["primary"], COLORS["secondary"], COLORS["negative"], COLORS["accent"]]
    data = [deltas, gammas, thetas, vegas]
    names = ["Delta", "Gamma", "Theta", "Vega"]

    for i, (d, c, n) in enumerate(zip(data, colors, names)):
        row = i // 2 + 1
        col = i % 2 + 1
        fig.add_trace(
            go.Scatter(
                x=days, y=d,
                line=dict(color=c, width=2),
                name=n,
                hovertemplate=f"Ngày: %{{x:.0f}}<br>{n}: %{{y:.6f}}<extra></extra>",
            ),
            row=row, col=col,
        )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Greeks theo Thời Gian Còn Lại", font=dict(size=14)),
        height=500,
        showlegend=False,
    )

    for i in range(1, 5):
        row = (i - 1) // 2 + 1
        col = (i - 1) % 2 + 1
        fig.update_xaxes(title_text="Số ngày còn lại", row=row, col=col,
                         gridcolor=COLORS["grid"], title_font=dict(size=10, color="#8896AB"))
        fig.update_yaxes(gridcolor=COLORS["grid"], row=row, col=col)

    return fig


def create_scenario_heatmap(scenario_data, price_changes, vol_changes):
    """Heatmap kịch bản giá CW."""
    z_data = []
    for dp in price_changes:
        row = []
        for dv in vol_changes:
            row.append(scenario_data.get((dp, dv), 0))
        z_data.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[f"Vol {dv:+d}%" for dv in vol_changes],
        y=[f"Giá {dp:+d}%" for dp in price_changes],
        colorscale="RdYlGn",
        text=[[f"{v:,.0f}" for v in row] for row in z_data],
        texttemplate="%{text}",
        textfont={"size": 11, "family": "Fira Code, monospace"},
        hovertemplate=(
            "Thay đổi giá: %{y}<br>"
            "Thay đổi vol: %{x}<br>"
            "Giá CW: %{z:,.0f} đ<extra></extra>"
        ),
        colorbar=dict(title=dict(text="Giá CW (đ)", font=dict(size=11, color="#8896AB"))),
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Ma Trận Kịch Bản Giá CW (đ)", font=dict(size=14)),
        height=450,
    )
    _apply_axis_style(fig, "Thay Đổi Biến Động", "Thay Đổi Giá Cơ Sở")

    return fig


def create_3d_surface(S, K, T, r, cr, option_type, q=0.0):
    """Biểu đồ 3D surface: Giá CW theo giá cơ sở và volatility."""
    S_range = np.linspace(S * 0.6, S * 1.4, 40)
    sigma_range = np.linspace(0.05, 1.0, 40)

    Z = np.zeros((len(sigma_range), len(S_range)))
    for i, sig in enumerate(sigma_range):
        for j, s in enumerate(S_range):
            model = BlackScholesModel(s, K, T, r, sig, option_type, q=q)
            Z[i, j] = model.price() / cr

    fig = go.Figure(data=[go.Surface(
        z=Z,
        x=S_range,
        y=sigma_range * 100,
        colorscale="Viridis",
        hovertemplate=(
            "Giá cơ sở: %{x:,.0f} đ<br>"
            "Volatility: %{y:.1f}%<br>"
            "Giá CW: %{z:,.0f} đ<extra></extra>"
        ),
        colorbar=dict(title=dict(text="Giá CW (đ)", font=dict(size=11, color="#8896AB"))),
    )])

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Giá CW theo Giá Cơ Sở & Volatility", font=dict(size=14)),
        scene=dict(
            xaxis_title="Giá Cơ Sở (đ)",
            yaxis_title="Volatility (%)",
            zaxis_title="Giá CW (đ)",
            bgcolor=COLORS["bg"],
        ),
        height=550,
    )

    return fig


def create_iv_sensitivity(S, K, T, r, cr, option_type, current_sigma, q=0.0):
    """Biểu đồ giá CW theo các mức volatility khác nhau."""
    sigmas = np.linspace(0.05, 1.0, 100)
    prices = []
    for sig in sigmas:
        model = BlackScholesModel(S, K, T, r, sig, option_type, q=q)
        prices.append(model.price() / cr)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sigmas * 100, y=prices,
        name="Giá CW lý thuyết",
        line=dict(color=COLORS["primary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(255, 107, 53, 0.06)",
        hovertemplate="Volatility: %{x:.1f}%<br>Giá CW: %{y:,.0f} đ<extra></extra>",
    ))

    # Đánh dấu sigma hiện tại
    model = BlackScholesModel(S, K, T, r, current_sigma, option_type, q=q)
    current_price = model.price() / cr
    fig.add_trace(go.Scatter(
        x=[current_sigma * 100], y=[current_price],
        name=f"σ hiện tại ({current_sigma*100:.1f}%)",
        mode="markers",
        marker=dict(color=COLORS["accent"], size=14, symbol="diamond",
                    line=dict(color="white", width=1.5)),
        hovertemplate=f"σ = {current_sigma*100:.1f}%<br>Giá CW: {current_price:,.0f} đ<extra></extra>",
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Độ Nhạy Giá CW theo Volatility", font=dict(size=14)),
        height=400,
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)"),
    )
    _apply_axis_style(fig, "Volatility (%)", "Giá CW (đ)")

    return fig


def create_time_decay_chart(time_decay_data, cw_market_price):
    """Biểu đồ suy giảm giá trị theo thời gian."""
    days = [d["days"] for d in time_decay_data]
    prices = [d["price"] for d in time_decay_data]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=days, y=prices,
        name="Giá CW lý thuyết",
        line=dict(color=COLORS["primary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(255, 107, 53, 0.1)",
        hovertemplate="Ngày còn lại: %{x:.0f}<br>Giá CW: %{y:,.0f} đ<extra></extra>",
    ))

    fig.add_hline(
        y=cw_market_price, line_dash="dash", line_color=COLORS["accent"],
        annotation_text=f"Giá thị trường: {cw_market_price:,.0f} đ",
        annotation_font=dict(size=11, color=COLORS["accent"]),
    )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Suy Giảm Giá Trị Theo Thời Gian (Time Decay)", font=dict(size=14)),
        height=400,
    )
    _apply_axis_style(fig, "Số Ngày Còn Lại", "Giá CW (đ)")

    return fig


# ========== CHARTS CHO TAB SO SÁNH CW ==========

CW_COLORS = [COLORS["primary"], COLORS["secondary"], COLORS["accent"], COLORS["purple"], COLORS["blue"]]


def create_radar_chart(cw_names, normalized_metrics):
    """Radar/Spider chart so sánh chỉ số chuẩn hóa giữa các CW.

    Args:
        cw_names: list of CW code strings
        normalized_metrics: dict {cw_name: {metric_name: 0-100 value}}
    """
    categories = list(next(iter(normalized_metrics.values())).keys())
    categories_closed = categories + [categories[0]]  # close the polygon

    fig = go.Figure()

    for idx, name in enumerate(cw_names):
        values = [normalized_metrics[name].get(c, 0) for c in categories]
        values_closed = values + [values[0]]

        color = CW_COLORS[idx % len(CW_COLORS)]
        # Convert hex color to rgba for fill
        hex_c = color.lstrip("#")
        r_c, g_c, b_c = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
        fill_color = f"rgba({r_c},{g_c},{b_c},0.08)"

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            name=name,
            line=dict(color=color, width=2.5),
            fill="toself",
            fillcolor=fill_color,
            hovertemplate=f"<b>{name}</b><br>%{{theta}}: %{{r:.1f}}<extra></extra>",
        ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="So Sánh Chỉ Số (Chuẩn Hóa 0-100)", font=dict(size=14)),
        polar=dict(
            bgcolor=COLORS["bg"],
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor=COLORS["grid"],
                tickfont=dict(size=9, color="#718096"),
            ),
            angularaxis=dict(
                gridcolor=COLORS["grid"],
                tickfont=dict(size=11, color="#CBD5E0"),
            ),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)"),
        height=450,
    )

    return fig


def create_comparison_bar_chart(cw_names, metrics_dict):
    """Grouped bar chart so sánh các chỉ số chính.

    Args:
        cw_names: list of CW codes
        metrics_dict: dict {metric_label: [value_cw1, value_cw2, ...]}
    """
    fig = go.Figure()

    for idx, name in enumerate(cw_names):
        color = CW_COLORS[idx % len(CW_COLORS)]
        values = [metrics_dict[m][idx] for m in metrics_dict]
        fig.add_trace(go.Bar(
            name=name,
            x=list(metrics_dict.keys()),
            y=values,
            marker_color=color,
            hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.2f}}<extra></extra>",
        ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="So Sánh Chỉ Số Chính", font=dict(size=14)),
        barmode="group",
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)"),
        height=400,
    )
    _apply_axis_style(fig, "", "Giá Trị")

    return fig


def create_overlaid_payoff(cw_data_list):
    """Biểu đồ payoff chồng lên nhau cho nhiều CW.

    Args:
        cw_data_list: list of dicts, each with keys:
            name, S, K, cw_price, cr, option_type
    """
    # Tính khoảng giá chung
    all_S = [d["S"] for d in cw_data_list]
    all_K = [d["K"] for d in cw_data_list]
    s_min = min(all_S + all_K) * 0.5
    s_max = max(all_S + all_K) * 1.5
    S_range = np.linspace(s_min, s_max, 300)

    fig = go.Figure()

    for idx, cw in enumerate(cw_data_list):
        color = CW_COLORS[idx % len(CW_COLORS)]
        name = cw["name"]
        K = cw["K"]
        cr = cw["cr"]
        cw_price = cw["cw_price"]

        if cw["option_type"] == "call":
            payoff = np.maximum(S_range - K, 0) / cr - cw_price
            be = K + cw_price * cr
        else:
            payoff = np.maximum(K - S_range, 0) / cr - cw_price
            be = K - cw_price * cr

        fig.add_trace(go.Scatter(
            x=S_range, y=payoff,
            name=name,
            line=dict(color=color, width=2.5),
            hovertemplate=(
                f"<b>{name}</b><br>"
                f"Giá CS: %{{x:,.0f}} đ<br>"
                f"Lợi nhuận: %{{y:,.0f}} đ<extra></extra>"
            ),
        ))

        # Break-even line
        fig.add_vline(
            x=be, line_dash="dash", line_color=color, opacity=0.5,
            annotation_text=f"HV {name}: {be:,.0f}",
            annotation_font=dict(size=9, color=color),
            annotation_position="top" if idx % 2 == 0 else "bottom",
        )

    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["neutral"], opacity=0.5)

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="So Sánh Lợi Nhuận Tại Đáo Hạn (Payoff)", font=dict(size=14)),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)"),
        height=500,
    )
    _apply_axis_style(fig, "Giá Cổ Phiếu Cơ Sở (đ)", "Lợi Nhuận / Lỗ (đ)")

    return fig


# ============================================================
# BUDGET ALLOCATION CHARTS
# ============================================================

def create_budget_pie_chart(allocations):
    """
    Biểu đồ Pie phân bổ ngân sách.
    allocations: list of {"name": str, "amount": float, "pct": float}
    """
    labels = [a["name"] for a in allocations]
    values = [a["amount"] for a in allocations]

    pie_colors = [
        "#FF6B35", "#4ECDC4", "#FFE66D", "#A78BFA", "#3B82F6",
        "#F43F5E", "#22C55E", "#F59E0B", "#06B6D4", "#8B5CF6",
        "#EC4899", "#14B8A6", "#EAB308", "#6366F1", "#D946EF",
    ]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=pie_colors[:len(labels)],
                    line=dict(color="#0E1117", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#F1F5F9"),
        hovertemplate="<b>%{label}</b><br>"
                      "Phân bổ: %{value:,.0f} đ<br>"
                      "Tỷ trọng: %{percent}<extra></extra>",
    )])

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Phân Bổ Ngân Sách Đầu Tư", font=dict(size=14)),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="rgba(255,255,255,0.1)",
            font=dict(size=10),
        ),
        height=420,
        annotations=[dict(
            text="Ngân<br>Sách",
            x=0.5, y=0.5, font_size=13, font_color="#94A3B8",
            showarrow=False,
        )],
    )
    return fig


def create_budget_bar_chart(allocations):
    """
    Biểu đồ Bar phân bổ — số lượng CW + chi phí.
    allocations: list of {"name": str, "qty": int, "amount": float, "pct": float}
    """
    names = [a["name"] for a in allocations]
    amounts = [a["amount"] for a in allocations]
    qtys = [a["qty"] for a in allocations]
    pcts = [a["pct"] for a in allocations]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=names,
        y=amounts,
        name="Chi Phí (đ)",
        marker=dict(color=COLORS["primary"], opacity=0.85),
        text=[f"{q:,} CW<br>{p:.1f}%" for q, p in zip(qtys, pcts)],
        textposition="auto",
        textfont=dict(size=10, color="#F1F5F9"),
        hovertemplate="<b>%{x}</b><br>"
                      "Chi phí: %{y:,.0f} đ<br>"
                      "<extra></extra>",
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Chi Phí & Số Lượng CW", font=dict(size=14)),
        showlegend=False,
        height=420,
    )
    _apply_axis_style(fig, "Mã CW", "Chi Phí (đ)")

    return fig


# ============================================================
# MARKOWITZ EFFICIENT FRONTIER
# ============================================================

def create_efficient_frontier_chart(frontier, assets, max_sharpe_metrics,
                                    min_var_metrics, max_sharpe_weights,
                                    min_var_weights):
    """
    Biểu đồ Efficient Frontier — scatter plot + 2 portfolio tối ưu.

    Parameters:
        frontier: dict from generate_efficient_frontier()
        assets: list[CWAsset]
        max_sharpe_metrics: (return, vol, sharpe)
        min_var_metrics: (return, vol, sharpe)
        max_sharpe_weights, min_var_weights: np.ndarray
    """
    fig = go.Figure()

    # 1. Scatter: random portfolios (color = Sharpe)
    fig.add_trace(go.Scatter(
        x=frontier["volatilities"] * 100,
        y=frontier["returns"] * 100,
        mode="markers",
        marker=dict(
            size=3,
            color=frontier["sharpes"],
            colorscale="Viridis",
            colorbar=dict(
                title=dict(text="Sharpe", font=dict(size=10)),
                thickness=12,
                len=0.6,
            ),
            opacity=0.5,
            line=dict(width=0),
        ),
        name="Random Portfolios",
        hovertemplate=(
            "Return: %{y:.1f}%<br>"
            "Risk: %{x:.1f}%<br>"
            "<extra></extra>"
        ),
    ))

    # 2. Max Sharpe portfolio (star)
    fig.add_trace(go.Scatter(
        x=[max_sharpe_metrics[1] * 100],
        y=[max_sharpe_metrics[0] * 100],
        mode="markers+text",
        marker=dict(
            size=18, color="#FFD700", symbol="star",
            line=dict(width=2, color="#0E1117"),
        ),
        name=f"Max Sharpe ({max_sharpe_metrics[2]:.2f})",
        text=["Max Sharpe"],
        textposition="top center",
        textfont=dict(size=10, color="#FFD700"),
        hovertemplate=(
            "<b>Max Sharpe Portfolio</b><br>"
            f"Sharpe: {max_sharpe_metrics[2]:.3f}<br>"
            "Return: %{y:.1f}%<br>"
            "Risk: %{x:.1f}%<br>"
            "<extra></extra>"
        ),
    ))

    # 3. Min Variance portfolio (diamond)
    fig.add_trace(go.Scatter(
        x=[min_var_metrics[1] * 100],
        y=[min_var_metrics[0] * 100],
        mode="markers+text",
        marker=dict(
            size=16, color="#4ECDC4", symbol="diamond",
            line=dict(width=2, color="#0E1117"),
        ),
        name=f"Min Variance (σ={min_var_metrics[1]*100:.1f}%)",
        text=["Min Risk"],
        textposition="bottom center",
        textfont=dict(size=10, color="#4ECDC4"),
        hovertemplate=(
            "<b>Min Variance Portfolio</b><br>"
            f"Sharpe: {min_var_metrics[2]:.3f}<br>"
            "Return: %{y:.1f}%<br>"
            "Risk: %{x:.1f}%<br>"
            "<extra></extra>"
        ),
    ))

    # 4. Individual CW assets (circles)
    for i, asset in enumerate(assets):
        fig.add_trace(go.Scatter(
            x=[asset.volatility * 100],
            y=[asset.expected_return * 100],
            mode="markers+text",
            marker=dict(
                size=10, color=COLORS["primary"], opacity=0.9,
                line=dict(width=1, color="#F1F5F9"),
            ),
            name=asset.name,
            text=[asset.name],
            textposition="top right",
            textfont=dict(size=9, color="#CBD5E0"),
            hovertemplate=(
                f"<b>{asset.name}</b><br>"
                "Return: %{y:.1f}%<br>"
                "Risk: %{x:.1f}%<br>"
                f"Score: {asset.score}/100<br>"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Efficient Frontier — Markowitz", font=dict(size=14)),
        legend=dict(
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="rgba(255,255,255,0.1)",
            font=dict(size=10),
            yanchor="bottom", y=0.02,
            xanchor="right", x=0.98,
        ),
        height=500,
    )
    _apply_axis_style(fig, "Rủi Ro (Volatility %)", "Kỳ Vọng Lợi Nhuận (%)")

    return fig


def create_weights_comparison_chart(asset_names, max_sharpe_weights,
                                    min_var_weights):
    """
    Biểu đồ Bar so sánh tỷ trọng giữa Max Sharpe và Min Variance.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=asset_names,
        y=[w * 100 for w in max_sharpe_weights],
        name="Max Sharpe",
        marker=dict(color="#FFD700", opacity=0.85),
        text=[f"{w*100:.1f}%" for w in max_sharpe_weights],
        textposition="auto",
        textfont=dict(size=10, color="#0E1117"),
    ))

    fig.add_trace(go.Bar(
        x=asset_names,
        y=[w * 100 for w in min_var_weights],
        name="Min Variance",
        marker=dict(color="#4ECDC4", opacity=0.85),
        text=[f"{w*100:.1f}%" for w in min_var_weights],
        textposition="auto",
        textfont=dict(size=10, color="#0E1117"),
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="So Sánh Tỷ Trọng: Max Sharpe vs Min Variance",
                   font=dict(size=14)),
        barmode="group",
        legend=dict(
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="rgba(255,255,255,0.1)",
            font=dict(size=10),
        ),
        height=400,
    )
    _apply_axis_style(fig, "Mã CW", "Tỷ Trọng (%)")

    return fig


# ============================================================
# BATCH ANALYSIS CHARTS
# ============================================================

def create_batch_pd_bar(names, pd_pcts):
    """
    Horizontal bar chart: Premium/Discount % cho từng CW.
    names: list[str], pd_pcts: list[float]
    """
    colors = [COLORS["positive"] if v < 0 else COLORS["negative"] for v in pd_pcts]

    fig = go.Figure(go.Bar(
        y=names, x=pd_pcts, orientation='h',
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in pd_pcts],
        textposition="auto",
        textfont=dict(size=10, color="#F1F5F9"),
        hovertemplate="<b>%{y}</b><br>P/D: %{x:+.1f}%<extra></extra>",
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Premium / Discount Từng CW", font=dict(size=14)),
        height=max(250, len(names) * 40 + 100),
        showlegend=False,
    )
    _apply_axis_style(fig, "Premium / Discount (%)", "")
    fig.add_vline(x=0, line_dash="dot", line_color=COLORS["neutral"], opacity=0.5)

    return fig


def create_batch_leverage_scatter(names, pd_pcts, leverages):
    """
    Scatter: Effective Leverage vs Premium/Discount %.
    names: list[str], pd_pcts: list[float], leverages: list[float]
    """
    colors = [COLORS["positive"] if v < 0 else COLORS["negative"] for v in pd_pcts]

    fig = go.Figure(go.Scatter(
        x=pd_pcts, y=leverages,
        mode="markers+text",
        text=names,
        textposition="top center",
        textfont=dict(size=9, color="#CBD5E0"),
        marker=dict(
            size=12, color=colors,
            line=dict(width=1, color="#F1F5F9"),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "P/D: %{x:+.1f}%<br>"
            "Đòn bẩy: %{y:.1f}x<extra></extra>"
        ),
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Đòn Bẩy vs Định Giá", font=dict(size=14)),
        height=350,
        showlegend=False,
    )
    _apply_axis_style(fig, "Premium / Discount (%)", "Đòn Bẩy Hiệu Dụng (x)")
    fig.add_vline(x=0, line_dash="dot", line_color=COLORS["neutral"], opacity=0.5)

    return fig


# ============================================================
# DAILY TRACKER CHARTS
# ============================================================

_DAILY_LEGEND = dict(
    orientation="h", yanchor="bottom", y=1.02,
    xanchor="right", x=1, font=dict(size=10),
)


def _format_daily_dates(records):
    """Convert YYYY-MM-DD dates to DD/MM for chart display."""
    from datetime import datetime as _dt
    formatted = []
    for r in records:
        raw = r.get("date", "")
        try:
            formatted.append(_dt.strptime(raw, "%Y-%m-%d").strftime("%d/%m"))
        except (ValueError, TypeError):
            formatted.append(raw)
    return formatted


def create_daily_price_chart(records):
    """
    Biểu đồ giá: S (spot), CW market price, theoretical price theo thời gian.
    Dual Y-axis: Left = S (spot), Right = CW price + Theo price.
    """
    dates = _format_daily_dates(records)
    S_vals = [r.get("S") for r in records]
    cw_vals = [r.get("cw_price") for r in records]
    theo_vals = [r.get("theoretical_price") for r in records]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Left Y: Spot price (green)
    fig.add_trace(go.Scatter(
        x=dates, y=S_vals,
        name="Cơ Sở (S) ←",
        line=dict(color=COLORS["positive"], width=2),
        hovertemplate="S: %{y:,.0f} đ<extra></extra>",
    ), secondary_y=False)

    # Right Y: CW market price (orange solid)
    fig.add_trace(go.Scatter(
        x=dates, y=cw_vals,
        name="CW Thực Tế →",
        line=dict(color=COLORS["primary"], width=2.5),
        hovertemplate="CW: %{y:,.0f} đ<extra></extra>",
    ), secondary_y=True)

    # Right Y: Theoretical price (teal dashed)
    fig.add_trace(go.Scatter(
        x=dates, y=theo_vals,
        name="CW Lý Thuyết →",
        line=dict(color=COLORS["secondary"], width=2, dash="dash"),
        hovertemplate="LT: %{y:,.0f} đ<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Biến Động Giá", font=dict(size=14)),
        height=420,
        hovermode="x unified",
        legend=_DAILY_LEGEND,
    )

    fig.update_xaxes(
        gridcolor=COLORS["grid"], zeroline=False,
        title_font=dict(size=11, color="#94A3B8"),
    )
    fig.update_yaxes(
        title_text="Cơ Sở (đ)",
        gridcolor=COLORS["grid"], zeroline=False,
        title_font=dict(size=11, color=COLORS["positive"]),
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="CW (đ)",
        gridcolor="rgba(255,255,255,0.02)", zeroline=False,
        title_font=dict(size=11, color=COLORS["primary"]),
        secondary_y=True,
    )

    return fig


def create_daily_pd_chart(records):
    """
    Biểu đồ Premium/Discount % theo thời gian (area chart).
    Xanh = Discount (tốt), Đỏ = Premium (xấu).
    """
    dates = _format_daily_dates(records)
    pd_vals = [r.get("premium_discount_pct", 0) for r in records]

    # Tách thành 2 trace: positive (premium) và negative (discount)
    pos_vals = [v if v and v >= 0 else 0 for v in pd_vals]
    neg_vals = [v if v and v < 0 else 0 for v in pd_vals]

    fig = go.Figure()

    # Premium (positive, red fill)
    fig.add_trace(go.Scatter(
        x=dates, y=pos_vals,
        name="Premium (+)",
        fill="tozeroy",
        fillcolor="rgba(239,68,68,0.25)",
        line=dict(color=COLORS["negative"], width=1.5),
        hovertemplate="Premium: +%{y:.2f}%<extra></extra>",
    ))

    # Discount (negative, green fill)
    fig.add_trace(go.Scatter(
        x=dates, y=neg_vals,
        name="Discount (−)",
        fill="tozeroy",
        fillcolor="rgba(34,197,94,0.25)",
        line=dict(color=COLORS["positive"], width=1.5),
        hovertemplate="Discount: %{y:.2f}%<extra></extra>",
    ))

    # Full P/D line on top
    fig.add_trace(go.Scatter(
        x=dates, y=pd_vals,
        name="P/D %",
        line=dict(color="#F1F5F9", width=2),
        hovertemplate="P/D: %{y:+.2f}%<extra></extra>",
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Premium / Discount %", font=dict(size=14)),
        height=420,
        hovermode="x unified",
        legend=_DAILY_LEGEND,
    )
    _apply_axis_style(fig, "", "P/D (%)")
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["neutral"], opacity=0.6)

    return fig


def create_daily_greeks_chart(records):
    """
    Biểu đồ Greeks: Delta, Effective Leverage (left Y), Gamma (right Y).
    """
    dates = _format_daily_dates(records)
    delta_vals = [r.get("delta") for r in records]
    gamma_vals = [r.get("gamma") for r in records]
    lev_vals = [r.get("effective_leverage") for r in records]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Left Y: Delta (orange)
    fig.add_trace(go.Scatter(
        x=dates, y=delta_vals,
        name="Delta ←",
        line=dict(color=COLORS["primary"], width=2.5),
        hovertemplate="Delta: %{y:.4f}<extra></extra>",
    ), secondary_y=False)

    # Left Y: Effective Leverage (yellow dashed)
    fig.add_trace(go.Scatter(
        x=dates, y=lev_vals,
        name="Đòn Bẩy ←",
        line=dict(color=COLORS["accent"], width=2.5, dash="dash"),
        hovertemplate="Đòn bẩy: %{y:.2f}x<extra></extra>",
    ), secondary_y=False)

    # Right Y: Gamma (teal)
    fig.add_trace(go.Scatter(
        x=dates, y=gamma_vals,
        name="Gamma →",
        line=dict(color=COLORS["secondary"], width=2),
        hovertemplate="Gamma: %{y:.6f}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Greeks & Đòn Bẩy", font=dict(size=14)),
        height=420,
        hovermode="x unified",
        legend=_DAILY_LEGEND,
    )

    fig.update_xaxes(
        gridcolor=COLORS["grid"], zeroline=False,
        title_font=dict(size=11, color="#94A3B8"),
    )
    fig.update_yaxes(
        title_text="Delta / Đòn Bẩy",
        gridcolor=COLORS["grid"], zeroline=False,
        title_font=dict(size=11, color=COLORS["primary"]),
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Gamma",
        gridcolor="rgba(255,255,255,0.02)", zeroline=False,
        title_font=dict(size=11, color=COLORS["secondary"]),
        secondary_y=True,
    )

    return fig


def create_backtesting_chart(records):
    """
    Biểu đồ Backtesting: So sánh Giá CW Lý Thuyết vs Giá CW Thực Tế qua thời gian.
    Vùng fill đổi màu: xanh = Discount, đỏ = Premium.
    """
    dates = _format_daily_dates(records)
    cw_vals = [r.get("cw_price") for r in records]
    theo_vals = [r.get("theoretical_price") for r in records]

    fig = go.Figure()

    # Giá Lý Thuyết (teal dashed)
    fig.add_trace(go.Scatter(
        x=dates, y=theo_vals,
        name="Lý Thuyết (BS)",
        line=dict(color=COLORS["secondary"], width=2.5, dash="dash"),
        hovertemplate="LT: %{y:,.0f} đ<extra></extra>",
    ))

    # Giá Thực Tế (orange solid)
    fig.add_trace(go.Scatter(
        x=dates, y=cw_vals,
        name="Thực Tế (TT)",
        line=dict(color=COLORS["primary"], width=2.5),
        hovertemplate="TT: %{y:,.0f} đ<extra></extra>",
    ))

    # Vùng fill Premium (TT > LT) — đỏ
    premium_upper = []
    premium_lower = []
    for c, t in zip(cw_vals, theo_vals):
        if c is not None and t is not None and c > t:
            premium_upper.append(c)
            premium_lower.append(t)
        else:
            premium_upper.append(None)
            premium_lower.append(None)

    fig.add_trace(go.Scatter(
        x=dates, y=premium_lower,
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=premium_upper,
        fill="tonexty",
        fillcolor="rgba(239,68,68,0.15)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
        name="Premium",
    ))

    # Vùng fill Discount (TT < LT) — xanh
    disc_upper = []
    disc_lower = []
    for c, t in zip(cw_vals, theo_vals):
        if c is not None and t is not None and c < t:
            disc_upper.append(t)
            disc_lower.append(c)
        else:
            disc_upper.append(None)
            disc_lower.append(None)

    fig.add_trace(go.Scatter(
        x=dates, y=disc_lower,
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=disc_upper,
        fill="tonexty",
        fillcolor="rgba(34,197,94,0.15)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
        name="Discount",
    ))

    # Tính chênh lệch trung bình
    diffs = []
    for c, t in zip(cw_vals, theo_vals):
        if c is not None and t is not None and t > 0:
            diffs.append((c - t) / t * 100)
    avg_diff = sum(diffs) / len(diffs) if diffs else 0
    diff_color = COLORS["negative"] if avg_diff > 0 else COLORS["positive"]
    diff_label = "Premium" if avg_diff > 0 else "Discount"

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Backtesting", font=dict(size=14)),
        height=420,
        hovermode="x unified",
        legend=_DAILY_LEGEND,
        annotations=[
            dict(
                text=f"P/D TB: {avg_diff:+.2f}% ({diff_label})",
                xref="paper", yref="paper",
                x=0.02, y=0.97,
                showarrow=False,
                font=dict(size=11, color=diff_color, family="Fira Code, monospace"),
                bgcolor="rgba(10,13,18,0.85)",
                bordercolor=diff_color,
                borderwidth=1,
                borderpad=5,
            ),
        ],
    )

    _apply_axis_style(fig, "", "Giá CW (đ)")

    return fig


# ============================================================
# SCENARIO & STRESS TEST CHARTS
# ============================================================

def create_pnl_heatmap(z_data, y_labels, x_labels, be_y=None, current_marker=None):
    """
    P&L Heatmap: Giá CS (Y) × Ngày còn lại (X).
    z_data: 2D list [rows=price_levels][cols=time_steps]
    be_y: list of break-even price per time step (overlay line)
    current_marker: (x_idx, y_idx) for current position dot
    """
    fig = go.Figure()

    # Main heatmap
    fig.add_trace(go.Heatmap(
        z=z_data,
        x=x_labels,
        y=y_labels,
        colorscale=[
            [0, "#B91C1C"],      # Deep red (big loss)
            [0.3, "#EF4444"],    # Red
            [0.45, "#FCD34D"],   # Yellow (near zero)
            [0.5, "#FAFAFA"],    # White (break-even)
            [0.55, "#86EFAC"],   # Light green
            [0.7, "#22C55E"],    # Green
            [1, "#15803D"],      # Deep green (big gain)
        ],
        zmid=0,
        text=[[f"{v:+,.0f}" for v in row] for row in z_data],
        texttemplate="%{text}",
        textfont={"size": 9, "family": "Fira Code, monospace"},
        hovertemplate=(
            "Giá CS: %{y}<br>"
            "Ngày còn lại: %{x}<br>"
            "P&L: %{text} đ<extra></extra>"
        ),
        colorbar=dict(
            title=dict(text="P&L (đ)", font=dict(size=11, color="#8896AB")),
            tickfont=dict(size=10, color="#8896AB"),
        ),
    ))

    # Break-even overlay line
    if be_y is not None:
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=be_y,
            mode="lines",
            name="Break-Even",
            line=dict(color="#FFD700", width=2.5, dash="dash"),
            hovertemplate="HV: %{y:,.0f} đ<br>Ngày: %{x}<extra>Break-Even</extra>",
        ))

    # Current position marker
    if current_marker:
        cx, cy = current_marker
        fig.add_trace(go.Scatter(
            x=[cx], y=[cy],
            mode="markers+text",
            name="Hiện tại",
            marker=dict(size=14, color="#FF6B35", symbol="diamond",
                        line=dict(width=2, color="#FFF")),
            text=["⬤ NOW"],
            textfont=dict(size=10, color="#FF6B35"),
            textposition="top center",
        ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="P&L Heatmap: Giá Cơ Sở × Thời Gian", font=dict(size=14)),
        height=520,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=10, color="#8896AB"),
        ),
    )
    _apply_axis_style(fig, "Ngày Còn Lại", "Giá Cơ Sở (đ)")

    return fig


def create_breakeven_decay_chart(days_list, be_prices, current_S):
    """
    Break-Even Decay Curve.
    Shows how break-even price rises over time for call (or falls for put).
    """
    fig = go.Figure()

    # Base line: current spot price (invisible, added FIRST for fill reference)
    fig.add_trace(go.Scatter(
        x=days_list,
        y=[current_S] * len(days_list),
        mode="lines",
        name="Giá CS Hiện Tại",
        line=dict(color=COLORS["secondary"], width=1, dash="dash"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Break-even line (fills to previous trace = current_S line)
    fig.add_trace(go.Scatter(
        x=days_list,
        y=be_prices,
        mode="lines+markers",
        name="Điểm Hoà Vốn",
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=6, color=COLORS["primary"]),
        fill="tonexty",
        fillcolor="rgba(255, 107, 53, 0.12)",
        hovertemplate="Ngày %{x}: HV = %{y:,.0f} đ<extra></extra>",
    ))

    # Current spot price reference annotation
    fig.add_hline(
        y=current_S,
        line=dict(color=COLORS["secondary"], width=2, dash="dash"),
        annotation=dict(
            text=f"Giá CS hiện tại: {current_S:,.0f} đ",
            font=dict(size=10, color=COLORS["secondary"]),
        ),
    )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Break-Even Decay: Điểm Hoà Vốn Theo Thời Gian", font=dict(size=14)),
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=10, color="#8896AB"),
        ),
    )
    _apply_axis_style(fig, "Ngày Nắm Giữ", "Giá Cơ Sở (đ)")

    return fig


def create_vol_shock_heatmap(z_data, price_labels, iv_labels):
    """
    Volatility Shock Heatmap: ΔGiá CS (Y) × ΔIV (X).
    z_data: P&L at each (ΔS%, ΔIV) point.
    """
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=iv_labels,
        y=price_labels,
        colorscale=[
            [0, "#B91C1C"],
            [0.35, "#EF4444"],
            [0.45, "#FCD34D"],
            [0.5, "#FAFAFA"],
            [0.55, "#86EFAC"],
            [0.65, "#22C55E"],
            [1, "#15803D"],
        ],
        zmid=0,
        text=[[f"{v:+,.0f}" for v in row] for row in z_data],
        texttemplate="%{text}",
        textfont={"size": 10, "family": "Fira Code, monospace"},
        hovertemplate=(
            "ΔGiá CS: %{y}<br>"
            "ΔIV: %{x}<br>"
            "P&L: %{text} đ<extra></extra>"
        ),
        colorbar=dict(
            title=dict(text="P&L (đ)", font=dict(size=11, color="#8896AB")),
        ),
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="Volatility Shock: ΔGiá × ΔIV", font=dict(size=14)),
        height=450,
    )
    _apply_axis_style(fig, "Thay Đổi IV (points)", "Thay Đổi Giá CS (%)")
    return fig


# ============================================================
# MONTE CARLO CHARTS
# ============================================================

def create_mc_fan_chart(
    days: "np.ndarray",
    percentiles: dict,
    baseline: "np.ndarray",
    initial_pnl: float = 0.0,
) -> go.Figure:
    """
    Fan chart hiển thị phân phối PnL danh mục theo thời gian.

    Parameters
    ----------
    days        : mảng [0, 1, ..., holding_days]
    percentiles : {"p5", "p25", "p50", "p75", "p95"} — giá trị PnL
    baseline    : PnL nếu giá không đổi (time decay only)
    initial_pnl : PnL tại t=0 (luôn = 0)
    """
    fig = go.Figure()

    # Band p5–p95 (nhạt)
    fig.add_trace(go.Scatter(
        x=np.concatenate([days, days[::-1]]),
        y=np.concatenate([percentiles["p95"], percentiles["p5"][::-1]]),
        fill="toself",
        fillcolor="rgba(59,130,246,0.10)",
        line=dict(color="rgba(0,0,0,0)"),
        name="5% – 95%",
        showlegend=True,
        hoverinfo="skip",
    ))

    # Band p25–p75 (đậm hơn)
    fig.add_trace(go.Scatter(
        x=np.concatenate([days, days[::-1]]),
        y=np.concatenate([percentiles["p75"], percentiles["p25"][::-1]]),
        fill="toself",
        fillcolor="rgba(59,130,246,0.25)",
        line=dict(color="rgba(0,0,0,0)"),
        name="25% – 75%",
        showlegend=True,
        hoverinfo="skip",
    ))

    # Median (p50)
    fig.add_trace(go.Scatter(
        x=days, y=percentiles["p50"],
        mode="lines",
        line=dict(color="#3B82F6", width=2.5),
        name="Trung vị (p50)",
        hovertemplate="Trung vị: <b>%{y:+,.0f} đ</b><extra></extra>",
    ))

    # Đường baseline (time decay only — giá không đổi)
    baseline_arr = np.linspace(initial_pnl, float(baseline), len(days))
    fig.add_trace(go.Scatter(
        x=days, y=baseline_arr,
        mode="lines",
        line=dict(color=COLORS["primary"], width=1.5, dash="dash"),
        name="Baseline (giá không đổi)",
        hovertemplate="Baseline: <b>%{y:+,.0f} đ</b><extra></extra>",
    ))

    # Đường y=0
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.25)", line_width=1)

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="△ Hành Trình PnL Danh Mục — Các Kịch Bản Percentile", font=dict(size=14)),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    _apply_axis_style(fig, "Ngày giữ", "PnL (VNĐ)")
    fig.update_yaxes(tickformat=",.0f", hoverformat="+,.0f")
    return fig


def create_mc_distribution(
    pnl_final: "np.ndarray",
    var_level: float,
    cvar_level: float,
    pnl_baseline: float,
    confidence_level: float = 0.95,
) -> go.Figure:
    """
    Histogram phân phối PnL cuối kỳ kèm VaR/CVaR/Baseline markers.
    """
    fig = go.Figure()

    # Tính màu cho từng bin (đỏ nếu < 0, xanh nếu >= 0)
    counts, bin_edges = np.histogram(pnl_final, bins=60)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    colors_hist = [COLORS["negative"] if c < 0 else COLORS["positive"] for c in bin_centers]

    fig.add_trace(go.Bar(
        x=bin_centers,
        y=counts,
        marker_color=colors_hist,
        marker_opacity=0.75,
        name="Phân phối PnL",
        hovertemplate="PnL: %{x:,.0f}đ<br>Số paths: %{y}<extra></extra>",
    ))

    # VaR line
    conf_pct = int(confidence_level * 100)
    fig.add_vline(
        x=var_level,
        line_dash="dash", line_color=COLORS["negative"], line_width=2,
        annotation_text=f"VaR {conf_pct}%",
        annotation_position="top right",
        annotation_font_color=COLORS["negative"],
    )

    # CVaR line
    fig.add_vline(
        x=cvar_level,
        line_dash="solid", line_color="#FF4444", line_width=2,
        annotation_text=f"CVaR {conf_pct}%",
        annotation_position="top left",
        annotation_font_color="#FF4444",
    )

    # Baseline
    fig.add_vline(
        x=pnl_baseline,
        line_dash="dot", line_color=COLORS["primary"], line_width=1.5,
        annotation_text="Baseline",
        annotation_position="top",
        annotation_font_color=COLORS["primary"],
    )

    # Zero line
    fig.add_vline(
        x=0,
        line_dash="dot", line_color="rgba(255,255,255,0.3)", line_width=1,
    )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="▪ Phân Phối PnL Cuối Kỳ", font=dict(size=14)),
        height=380,
        bargap=0.05,
        showlegend=False,
    )
    _apply_axis_style(fig, "PnL Cuối Kỳ (VNĐ)", "Số Lượng Paths")
    fig.update_xaxes(tickformat=",.0f")
    return fig


def create_mc_contribution(
    cw_names: list,
    expected_pnl: list,
    std_pnl: list,
) -> go.Figure:
    """
    Horizontal bar chart đóng góp E[PnL] từng CW, kèm error bar 1σ.
    """
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in expected_pnl]

    fig = go.Figure(go.Bar(
        y=cw_names,
        x=expected_pnl,
        orientation="h",
        marker_color=colors,
        marker_opacity=0.85,
        error_x=dict(
            type="data",
            array=std_pnl,
            visible=True,
            color="rgba(255,255,255,0.4)",
            thickness=1.5,
            width=4,
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "E[PnL]: %{x:,.0f}đ<br>"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="▣ Đóng Góp PnL Kỳ Vọng Theo CW", font=dict(size=14)),
        height=max(260, 60 + len(cw_names) * 50),
        xaxis_tickformat=",.0f",
    )
    _apply_axis_style(fig, "E[PnL] (VNĐ)", "")
    return fig


# ── Hedging Charts ───────────────────────────────────────────────


def create_hedging_payoff_chart(payoff_data: dict) -> go.Figure:
    """
    Biểu đồ payoff tổng hợp CP + CW.
    3 đường: Stock PnL, CW PnL, Total PnL.
    """
    prices = payoff_data["prices"]
    stock_pnl = payoff_data["stock_pnl"]
    cw_pnl = payoff_data["cw_pnl"]
    total_pnl = payoff_data["total_pnl"]

    fig = go.Figure()

    # Stock PnL
    fig.add_trace(go.Scatter(
        x=prices, y=stock_pnl,
        name="PnL Cổ Phiếu",
        line=dict(color=COLORS["blue"], width=1.5, dash="dot"),
        hovertemplate="S = %{x:,.0f}<br>Stock PnL = %{y:,.0f} VNĐ<extra></extra>",
    ))

    # CW PnL
    fig.add_trace(go.Scatter(
        x=prices, y=cw_pnl,
        name="PnL Chứng Quyền",
        line=dict(color=COLORS["primary"], width=1.5, dash="dash"),
        hovertemplate="S = %{x:,.0f}<br>CW PnL = %{y:,.0f} VNĐ<extra></extra>",
    ))

    # Total PnL (bold white)
    fig.add_trace(go.Scatter(
        x=prices, y=total_pnl,
        name="PnL Tổng Hợp",
        line=dict(color="#FFFFFF", width=2.5),
        hovertemplate="S = %{x:,.0f}<br>Tổng PnL = %{y:,.0f} VNĐ<extra></extra>",
    ))

    # Fill profit zone (green) and loss zone (red)
    import numpy as np
    tp = np.array(total_pnl)
    fig.add_trace(go.Scatter(
        x=prices, y=[max(0, v) for v in total_pnl],
        fill="tozeroy",
        fillcolor="rgba(46,204,113,0.08)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=[min(0, v) for v in total_pnl],
        fill="tozeroy",
        fillcolor="rgba(231,76,60,0.08)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Zero line
    fig.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.2)", line_width=1)

    # Break-even markers
    for be in payoff_data.get("break_evens", []):
        fig.add_vline(
            x=be, line_dash="dot", line_color=COLORS["accent"], line_width=1,
            annotation_text=f"BE {be:,.0f}",
            annotation_position="top",
            annotation_font=dict(size=10, color=COLORS["accent"]),
        )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="◇ Payoff Diagram — Danh Mục Tổng Hợp", font=dict(size=14)),
        height=380,
        legend=dict(
            orientation="h", y=-0.18, x=0.5, xanchor="center",
            font=dict(size=11),
        ),
        xaxis_tickformat=",.0f",
        yaxis_tickformat=",.0f",
    )
    _apply_axis_style(fig, "Giá Cổ Phiếu (VNĐ)", "PnL (VNĐ)")
    return fig


def create_delta_exposure_chart(per_ticker: list[dict], target_delta: float = 0.0) -> go.Figure:
    """
    Stacked bar: Stock Delta + CW Delta per ticker.
    """
    tickers = [t["ticker"] for t in per_ticker]
    stock_deltas = [t["stock_delta"] for t in per_ticker]
    cw_deltas = [t["cw_delta"] for t in per_ticker]
    net_deltas = [t["stock_delta"] + t["cw_delta"] for t in per_ticker]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=tickers, y=stock_deltas,
        name="Delta Cổ Phiếu",
        marker_color=COLORS["blue"],
        hovertemplate="%{x}: Stock Δ = %{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=tickers, y=cw_deltas,
        name="Delta CW",
        marker_color=COLORS["primary"],
        hovertemplate="%{x}: CW Δ = %{y:,.1f}<extra></extra>",
    ))

    # Net delta line
    fig.add_trace(go.Scatter(
        x=tickers, y=net_deltas,
        name="Net Delta",
        mode="lines+markers",
        line=dict(color="#FFFFFF", width=2),
        marker=dict(size=8, color="#FFFFFF"),
        hovertemplate="%{x}: Net Δ = %{y:,.1f}<extra></extra>",
    ))

    # Target delta line
    if target_delta != 0:
        fig.add_hline(
            y=target_delta, line_dash="dash", line_color=COLORS["accent"], line_width=1.5,
            annotation_text=f"Target Δ = {target_delta:.1f}",
            annotation_position="top right",
            annotation_font=dict(size=10, color=COLORS["accent"]),
        )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="△ Delta Exposure Per Ticker", font=dict(size=14)),
        height=350,
        barmode="stack",
        legend=dict(
            orientation="h", y=-0.18, x=0.5, xanchor="center",
            font=dict(size=11),
        ),
        yaxis_tickformat=",.0f",
    )
    _apply_axis_style(fig, "", "Delta")
    return fig


def create_risk_profile_radar(profiles_data: list[dict]) -> go.Figure:
    """
    Radar chart so sánh 5 nhóm rủi ro.
    Axes: Return, Risk, Net Delta, Leverage, Protection.
    """
    categories = ["Lợi nhuận KV", "Rủi ro (σ)", "Net Delta", "Đòn bẩy", "Chi phí BV"]

    fig = go.Figure()

    for p in profiles_data:
        values = [
            p.get("expected_return", 0),
            p.get("risk", 0),
            p.get("net_delta_norm", 0),
            p.get("leverage_norm", 0),
            p.get("protection_cost_norm", 0),
        ]
        # Close the polygon
        values_closed = values + [values[0]]
        cats_closed = categories + [categories[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            name=p["name"],
            line=dict(color=p["color"], width=2),
            fill="toself",
            fillcolor=_hex_to_rgba(p["color"], 0.08),
        ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(text="◎ So Sánh Khẩu Vị Rủi Ro", font=dict(size=14)),
        height=400,
        polar=dict(
            bgcolor=COLORS["bg"],
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor=COLORS["grid"],
                tickfont=dict(size=9, color="#7A84A0"),
            ),
            angularaxis=dict(
                gridcolor=COLORS["grid"],
                tickfont=dict(size=11, color="#B8C2DB"),
            ),
        ),
        legend=dict(
            orientation="h", y=-0.12, x=0.5, xanchor="center",
            font=dict(size=10),
        ),
    )
    return fig


# ===== BACKTEST CHARTS =====

def create_backtest_price_chart(df, ma_cw: str):
    """
    Biểu đồ đường so sánh Giá Thị Trường vs Giá Lý Thuyết (Black-Scholes) theo thời gian.
    Phần diện tích giữa 2 đường thể hiện mức độ sai lệch định giá.
    """
    import pandas as pd

    fig = go.Figure()

    # Trace 1: Giá thị trường (line đặc — chủ đạo)
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["cw_price"],
        name="Giá Thị Trường",
        mode="lines+markers",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=5, color=COLORS["primary"]),
        hovertemplate=(
            "<b>%{x|%d/%m/%Y}</b><br>"
            "Giá TT: <b>%{y:,.2f} đ</b><extra>Thị Trường</extra>"
        ),
    ))

    # Trace 2: Giá lý thuyết (dashed + fill tonexty)
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["theoretical_price"],
        name="Giá Lý Thuyết (BS)",
        mode="lines+markers",
        line=dict(color=COLORS["secondary"], width=2, dash="dash"),
        marker=dict(size=4, color=COLORS["secondary"], symbol="diamond"),
        fill="tonexty",
        fillcolor=_hex_to_rgba(COLORS["primary"], 0.07),
        hovertemplate=(
            "<b>%{x|%d/%m/%Y}</b><br>"
            "Giá LT: <b>%{y:,.2f} đ</b><extra>Lý Thuyết BS</extra>"
        ),
    ))

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(
            text=f"<b>So Sánh Giá CW: {ma_cw}</b>",
            font=dict(size=15, color="#F0F4FF"),
            x=0.01,
        ),
        legend=dict(
            orientation="h", y=1.08, x=0, xanchor="left",
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
    )
    _apply_axis_style(fig, "Ngày", "Giá CW (đ)")
    return fig


def create_backtest_pd_chart(df, ma_cw: str):
    """
    Biểu đồ Bar: Premium/Discount % theo từng ngày.
    Cột xanh = Premium (giá TT > lý thuyết), cột đỏ = Discount.
    """
    pct_col = "premium_discount_pct"
    if pct_col not in df.columns:
        return None

    values = df[pct_col].fillna(0).tolist()
    bar_colors = [
        COLORS["positive"] if v >= 0 else COLORS["negative"]
        for v in values
    ]

    fig = go.Figure(go.Bar(
        x=df["date"],
        y=values,
        marker_color=bar_colors,
        marker_line_width=0,
        name="P/D %",
        hovertemplate=(
            "<b>%{x|%d/%m/%Y}</b><br>"
            "P/D: <b>%{y:+.2f}%</b><extra></extra>"
        ),
    ))

    # Đường 0 tham chiếu
    fig.add_hline(
        y=0,
        line_color=COLORS["neutral"],
        line_dash="dot",
        line_width=1.2,
        opacity=0.6,
    )

    fig.update_layout(
        **COMMON_LAYOUT,
        title=dict(
            text=f"<b>Premium / Discount % — {ma_cw}</b>",
            font=dict(size=14, color="#F0F4FF"),
            x=0.01,
        ),
        bargap=0.25,
    )
    _apply_axis_style(fig, "Ngày", "P/D %")
    return fig
