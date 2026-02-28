import sys
import os

# Đảm bảo thư mục gốc trong sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from ui.styles import inject_custom_css, inject_tab_navigation, inject_hide_github
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
    """Favicon: hình con bò bullish xanh lá (pixel art 64×64)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return "🐂"

    SIZE = 64
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    G  = (46, 204, 113, 255)    # #2ECC71 — xanh chính
    GD = (30, 150,  80, 255)    # xanh đậm — sừng, mõm, móng, đuôi
    BK = ( 8,  12,  10, 255)    # đen — mắt / lỗ mũi
    HL = (150, 230, 170, 200)   # highlight mắt

    # ── Thân (body) ──────────────────────────────────────────────
    d.ellipse([13, 24, 55, 45], fill=G)

    # ── Bướu vai (hump) ─────────────────────────────────────────
    d.ellipse([17, 17, 32, 32], fill=G)

    # ── Cổ — lấp khoảng trống giữa đầu và thân ─────────────────
    d.rectangle([12, 26, 22, 44], fill=G)

    # ── Đầu (vẽ sau cổ để phủ lên, không có kẽ hở) ──────────────
    d.ellipse([1, 17, 22, 37], fill=G)

    # ── Sừng (horns) ─────────────────────────────────────────────
    d.polygon([(4,  18), (9,  18), (6,  4)], fill=GD)   # sừng trái
    d.polygon([(13, 17), (18, 17), (21, 4)], fill=GD)   # sừng phải

    # ── Mõm (muzzle) ─────────────────────────────────────────────
    d.ellipse([1, 29, 11, 37], fill=GD)
    # Lỗ mũi
    d.ellipse([2,  32, 5,  35], fill=BK)
    d.ellipse([7,  32, 10, 35], fill=BK)

    # ── Mắt ──────────────────────────────────────────────────────
    d.ellipse([6, 19, 13, 26], fill=BK)
    d.ellipse([7, 20, 10, 23], fill=HL)     # điểm sáng

    # ── Chân trước ───────────────────────────────────────────────
    d.rectangle([16, 44, 21, 61], fill=G)
    d.rectangle([24, 44, 29, 61], fill=G)
    d.rectangle([16, 60, 21, 63], fill=GD)  # móng
    d.rectangle([24, 60, 29, 63], fill=GD)

    # ── Chân sau ─────────────────────────────────────────────────
    d.rectangle([39, 44, 44, 61], fill=G)
    d.rectangle([47, 44, 52, 61], fill=G)
    d.rectangle([39, 60, 44, 63], fill=GD)
    d.rectangle([47, 60, 52, 63], fill=GD)

    # ── Đuôi (cuộn lên trên) ─────────────────────────────────────
    d.line([(54, 32), (59, 22), (62, 13)], fill=GD, width=3)

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

# Ẩn icon GitHub (parent frame)
inject_hide_github()

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
