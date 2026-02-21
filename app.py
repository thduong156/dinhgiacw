import sys
import os

# Đảm bảo thư mục gốc trong sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from ui.styles import inject_custom_css
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
from data.portfolio_manager import load_portfolio, deserialize_cw_entry

# Page config
st.set_page_config(
    page_title="Phân Tích Chứng Quyền - Black-Scholes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS
inject_custom_css()

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

# Tabs — workflow order: Định giá → Phân tích loạt → So sánh → Greeks → Đề xuất → Dự báo → IV → Kịch bản → Theo dõi
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📈 Định Giá CW",
    "📋 Phân Tích Hàng Loạt",
    "🔀 So Sánh CW",
    "📊 Chỉ Số Hy Lạp",
    "🏅 Đề Xuất CW",
    "🔮 Dự Báo & Đòn Bẩy",
    "📉 Biến Động Ngầm Định",
    "🎯 Kịch Bản & Stress Test",
    "📅 Theo Dõi Hàng Ngày",
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
