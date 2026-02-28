import sys
import os

# Đảm bảo thư mục gốc trong sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from ui.styles import inject_custom_css, inject_tab_navigation
from ui.components import render_header, parameter_sidebar
from ui.tab_recommend import render_recommend_tab
from ui.tab_batch import render_batch_tab
from ui.tab_cw_compare import render_cw_compare_tab
from ui.tab_pricing import render_pricing_tab
from ui.tab_forecast import render_forecast_tab
from ui.tab_greeks import render_greeks_tab
from ui.tab_iv import render_iv_tab
from ui.tab_daily_tracker import render_daily_tracker_tab
from ui.tab_scenario import render_scenario_tab
from ui.tab_monte_carlo import render_monte_carlo_tab
from ui.tab_hedging import render_hedging_tab
from data.portfolio_manager import load_portfolio, deserialize_cw_entry


def _make_bullish_icon():
    """Tạo favicon bullish xanh lá: 3 nến tăng dần + đường xu hướng xanh."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return "🐂"

    SIZE = 64
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Màu xanh bullish (#2ECC71 palette)
    C_BODY   = (46,  204, 113, 255)   # #2ECC71 — thân nến xanh
    C_WICK   = (39,  174,  96, 230)   # #27AE60 — bấc nến xanh đậm hơn
    C_TREND  = (88,  214, 141, 210)   # #58D68D — đường xu hướng xanh nhạt
    C_GLOW   = (46,  204, 113,  45)   # hào quang nhẹ xung quanh thân

    # 3 nến bullish tăng dần: (x_tâm, y_bấc_trên, y_thân_trên, y_thân_dưới, y_bấc_dưới)
    candles = [
        (12, 38, 42, 56, 60),   # nến trái  — thấp nhất
        (32, 20, 24, 40, 44),   # nến giữa
        (52,  3,  7, 22, 26),   # nến phải  — cao nhất
    ]
    half = 7

    for x, wt, bt, bb, wb in candles:
        # Hào quang mờ (glow) xung quanh thân
        d.rectangle([x - half - 2, bt - 1, x + half + 2, bb + 1], fill=C_GLOW)
        # Bấc trên & dưới
        d.line([(x, wt), (x, bt)], fill=C_WICK, width=2)
        d.line([(x, bb), (x, wb)], fill=C_WICK, width=2)
        # Thân nến xanh
        d.rectangle([x - half, bt, x + half, bb], fill=C_BODY)

    # Đường xu hướng tăng: dưới-trái → trên-phải (nét đôi để rõ hơn)
    d.line([(3, 57), (61, 11)], fill=C_TREND, width=2)

    return img


# Page config
st.set_page_config(
    page_title="Phân Tích Chứng Quyền - Black-Scholes",
    page_icon=_make_bullish_icon(),
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS
inject_custom_css()

# Inject tab navigation arrows
inject_tab_navigation()

# Header
render_header()

# Load default portfolio on first run (trước khi sidebar render)
if "cw_portfolio" not in st.session_state:
    default_data = load_portfolio("default")
    if default_data:
        all_cw = [
            deserialize_cw_entry(cw)
            for cw in default_data.get("cw_list", [])
        ]
        if all_cw:
            st.session_state["_loaded_portfolio_cw"] = all_cw

# Sidebar — returns selected CW or None
selected_cw = parameter_sidebar()

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "◈ Định Giá CW",
    "≡ Phân Tích Hàng Loạt",
    "⇌ So Sánh CW",
    "Δ Chỉ Số Hy Lạp",
    "★ Đề Xuất CW",
    "◇ Dự Báo & Đòn Bẩy",
    "σ Biến Động Ngầm Định",
    "⊕ Kịch Bản & Stress Test",
    "⊡ Theo Dõi & Backtest",
    "∿ Monte Carlo",
    "⊘ Phòng Hộ",
])

with tab1:
    render_pricing_tab(selected_cw)

with tab2:
    render_batch_tab()

with tab3:
    render_cw_compare_tab()

with tab4:
    render_greeks_tab(selected_cw)

with tab5:
    render_recommend_tab()

with tab6:
    render_forecast_tab(selected_cw)

with tab7:
    render_iv_tab(selected_cw)

with tab8:
    render_scenario_tab(selected_cw)

with tab9:
    render_daily_tracker_tab()

with tab10:
    render_monte_carlo_tab()

with tab11:
    render_hedging_tab()

# Footer
st.markdown(
    '<div class="app-footer-v2">'
    '<div class="app-footer-v2-line"></div>'
    '<div class="app-footer-v2-brand">CW Analyzer &bull; Covered Warrant Analysis Tool</div>'
    '<div class="app-footer-v2-disclaimer">'
    'Công cụ chỉ mang tính chất tham khảo, sử dụng mô hình Black-Scholes. '
    'Không phải là khuyến nghị đầu tư.'
    '</div>'
    '<div class="app-footer-v2-designer">Thiết kế bởi THDUONG156</div>'
    '</div>',
    unsafe_allow_html=True,
)
