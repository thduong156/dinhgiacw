import streamlit as st


def inject_custom_css():
    """Inject CSS tùy chỉnh cho giao diện chuyên nghiệp — High Contrast Dark Theme."""
    st.markdown("""
    <style>
        /* ===== GOOGLE FONTS ===== */
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Noto+Sans+Symbols+2&display=swap');

        /* ===== GLOBAL FONT OVERRIDE — Fira Code everywhere ===== */
        *, *::before, *::after {
            font-family: 'Fira Code', 'Noto Sans Symbols 2', monospace !important;
            font-feature-settings: "liga" 0, "calt" 0 !important;
            -webkit-font-feature-settings: "liga" 0, "calt" 0 !important;
        }
        /* Khôi phục Material Icons cho Streamlit internal icons */
        span[data-testid="stIconMaterial"],
        .material-symbols-rounded,
        .material-symbols-outlined,
        .material-symbols-sharp {
            font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
            font-feature-settings: "liga" 1 !important;
            -webkit-font-feature-settings: "liga" 1 !important;
        }
        /* Preserve Noto Sans Symbols 2 for icon containers */
        .section-title-icon, .sb-brand-icon, .sb-empty-state-icon,
        .tab-empty-state-icon, .medal-card-icon {
            font-family: 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', 'Fira Code', monospace !important;
        }

        /*
         * COLOR PALETTE — High Contrast Dark
         * bg-base:    #0E1117  (nền chính)
         * bg-surface: #1A1D27  (thẻ, panel)
         * bg-raised:  #222633  (hover, raised cards)
         * border:     #2E3348  (viền mặc định)
         * border-hi:  #444C66  (viền nổi bật)
         * text-hi:    #F0F4FF  (chữ chính)
         * text-mid:   #B8C2DB  (chữ phụ)
         * text-lo:    #7A84A0  (nhãn, mờ)
         * accent:     #FFFFFF  (accent trắng tinh)
         * accent-dim: #C8CFDF  (accent mờ)
         */

        /* ===== GLOBAL ===== */
        html, body, [class*="css"] {
            font-family: 'Fira Code', 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', monospace;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
        }

        .stApp {
            background: #0E1117;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 7px; height: 7px; }
        ::-webkit-scrollbar-track { background: #0E1117; }
        ::-webkit-scrollbar-thumb {
            background: #2E3348;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: #444C66; }

        /* ===== HEADER ===== */
        .main-header {
            font-size: 2rem;
            font-weight: 700;
            font-family: 'Fira Code', monospace;
            color: #F0F4FF;
            text-align: center;
            padding: 0.4rem 0 0.3rem 0;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .sub-header {
            font-size: 0.85rem;
            color: #7A84A0;
            text-align: center;
            margin-top: -0.4rem;
            margin-bottom: 1.5rem;
            letter-spacing: 1px;
            font-weight: 400;
        }

        /* ===== SIDEBAR ===== */
        section[data-testid="stSidebar"] {
            background: #090C12;
            border-right: 1px solid #2E3348;
        }

        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stNumberInput label,
        section[data-testid="stSidebar"] .stSlider label,
        section[data-testid="stSidebar"] .stDateInput label,
        section[data-testid="stSidebar"] .stTextInput label,
        section[data-testid="stSidebar"] .stRadio label {
            color: #B8C2DB !important;
            font-weight: 500 !important;
            font-size: 0.82rem !important;
        }

        /* ===== SIDEBAR BRANDED HEADER ===== */
        .sb-brand {
            text-align: center;
            padding: 18px 12px 14px;
            margin: -8px -8px 12px;
            background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 100%);
            border-bottom: 1px solid #2E3348;
        }
        .sb-brand-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            font-family: 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', sans-serif;
            color: #F0F4FF;
            margin-bottom: 10px;
            opacity: 0.85;
        }
        .sb-brand-title {
            font-size: 1.15rem;
            font-weight: 700;
            font-family: 'Fira Code', monospace;
            color: #F0F4FF;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        .sb-brand-subtitle {
            font-size: 0.65rem;
            color: #7A84A0;
            letter-spacing: 1px;
            font-weight: 500;
        }

        /* ===== SIDEBAR SECTION HEADERS ===== */
        .sb-section {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 18px 0 12px;
            padding: 0;
        }
        .sb-section-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #FFFFFF;
            box-shadow: 0 0 8px rgba(255,255,255,0.5);
            flex-shrink: 0;
        }
        .sb-section-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: #B8C2DB;
            letter-spacing: 2px;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .sb-section-line {
            flex: 1;
            height: 1px;
            background: #2E3348;
        }

        /* ===== CW SELECTOR ===== */
        .sb-selector-wrapper {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            padding: 10px 12px 4px;
            margin-bottom: 8px;
        }
        .sb-selector-label {
            font-size: 0.65rem;
            font-weight: 600;
            color: #7A84A0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .sb-selector-label .pulse-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #FFFFFF;
            display: inline-block;
            animation: pulse-glow 2s ease-in-out infinite;
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 4px rgba(255,255,255,0.4); opacity: 0.8; }
            50% { box-shadow: 0 0 12px rgba(255,255,255,0.9); opacity: 1; }
        }

        /* ===== SUMMARY MINI-DASHBOARD ===== */
        .sb-dash {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 14px;
            margin-top: 8px;
        }
        .sb-dash-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #2E3348;
        }
        .sb-dash-cw-name {
            font-size: 0.95rem;
            font-weight: 700;
            color: #F0F4FF;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
        }
        .sb-dash-type-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .sb-dash-type-badge.call {
            background: rgba(255,255,255,0.12);
            color: #F0F4FF;
            border: 1px solid #444C66;
        }
        .sb-dash-type-badge.put {
            background: rgba(255,255,255,0.06);
            color: #B8C2DB;
            border: 1px solid #2E3348;
        }

        /* Moneyness badges */
        .sb-moneyness {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 10px;
            border-radius: 8px;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .sb-moneyness.itm {
            background: rgba(255,255,255,0.12);
            color: #F0F4FF;
            border: 1px solid #444C66;
        }
        .sb-moneyness.otm {
            background: rgba(255,255,255,0.04);
            color: #7A84A0;
            border: 1px solid #2E3348;
        }
        .sb-moneyness.atm {
            background: rgba(255,255,255,0.08);
            color: #B8C2DB;
            border: 1px solid #3A4055;
        }

        /* Mini metric grid */
        .sb-metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin: 10px 0;
        }
        .sb-metric-mini {
            background: #222633;
            border: 1px solid #2E3348;
            border-radius: 10px;
            padding: 10px 8px;
            text-align: center;
            transition: border-color 0.2s ease, background 0.2s ease;
        }
        .sb-metric-mini:hover {
            border-color: #444C66;
            background: #29303F;
        }
        .sb-metric-mini-label {
            font-size: 0.6rem;
            font-weight: 600;
            color: #7A84A0;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 4px;
        }
        .sb-metric-mini-value {
            font-size: 0.88rem;
            font-weight: 700;
            color: #F0F4FF;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
        }

        /* Time remaining progress bar */
        .sb-time-bar-wrapper { margin: 10px 0 4px; }
        .sb-time-bar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .sb-time-bar-label {
            font-size: 0.62rem;
            color: #7A84A0;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .sb-time-bar-value {
            font-size: 0.72rem;
            font-weight: 700;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            color: #B8C2DB;
        }
        .sb-time-bar {
            width: 100%;
            height: 6px;
            background: #222633;
            border-radius: 3px;
            overflow: hidden;
        }
        .sb-time-bar-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.6s ease;
        }

        /* ===== SIDEBAR DIVIDER ===== */
        .sb-divider {
            height: 1px;
            background: #2E3348;
            margin: 16px 0;
            border: none;
        }

        /* ===== PORTFOLIO CARDS v2 ===== */
        .sb-portfolio-count-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            background: #222633;
            color: #B8C2DB;
            border: 1px solid #2E3348;
            margin: 4px auto 10px;
        }
        .sb-portfolio-count-badge .count-num {
            font-weight: 800;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: #F0F4FF;
        }

        .sb-cw-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            padding: 12px;
            margin: 6px 0;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        .sb-cw-card::before {
            content: '';
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 3px;
            border-radius: 3px 0 0 3px;
            transition: background 0.2s ease;
        }
        .sb-cw-card.selected {
            border-color: #444C66;
            background: #222633;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }
        .sb-cw-card.selected::before { background: #FFFFFF; }
        .sb-cw-card:not(.selected)::before { background: #2E3348; }
        .sb-cw-card:hover {
            border-color: #3A4055;
            background: #1E2130;
        }
        .sb-cw-card-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .sb-cw-card-name {
            font-weight: 700;
            font-size: 0.82rem;
            color: #F0F4FF;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            padding-left: 6px;
        }
        .sb-cw-card-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.58rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .sb-cw-card-badge.call {
            background: rgba(255,255,255,0.1);
            color: #F0F4FF;
            border: 1px solid #444C66;
        }
        .sb-cw-card-badge.put {
            background: rgba(255,255,255,0.04);
            color: #B8C2DB;
            border: 1px solid #2E3348;
        }
        .sb-cw-card-stats {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
            padding-left: 6px;
        }
        .sb-cw-card-stat {
            font-size: 0.63rem;
            color: #B8C2DB;
            padding: 2px 6px;
            background: #222633;
            border-radius: 4px;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
        }
        .sb-cw-card-pnl {
            font-size: 0.65rem;
            font-weight: 700;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            padding: 3px 6px;
            margin-top: 4px;
        }

        /* ===== EMPTY STATE ===== */
        .sb-empty-state { text-align: center; padding: 24px 12px; }
        .sb-empty-state-icon { font-size: 2rem; margin-bottom: 8px; opacity: 0.4; font-family: 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', sans-serif; }
        .sb-empty-state-title {
            font-size: 0.82rem; font-weight: 600;
            color: #B8C2DB; margin-bottom: 4px;
        }
        .sb-empty-state-text { font-size: 0.72rem; color: #7A84A0; line-height: 1.5; }

        /* ===== METRIC CARDS ===== */
        div[data-testid="stMetric"] {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 18px 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            border-color: #444C66;
        }
        div[data-testid="stMetric"] label {
            color: #7A84A0 !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #F0F4FF !important;
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            font-family: 'Fira Code', 'JetBrains Mono', monospace !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] svg { display: inline; }

        /* ===== TABS ===== */
        /* Container bọc ngoài — relative để chứa mũi tên */
        .stTabs [data-baseweb="tab-list"] {
            gap: 3px;
            background: #1A1D27;
            border-radius: 14px;
            padding: 5px 36px;
            border: 1px solid #2E3348;
            overflow-x: auto;
            scroll-behavior: smooth;
            scrollbar-width: none;          /* Firefox */
            -ms-overflow-style: none;       /* IE/Edge */
            position: relative;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none;                  /* Chrome/Safari */
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 11px;
            padding: 10px 16px;
            font-weight: 500;
            font-family: 'Fira Code', 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', monospace;
            font-size: 0.82rem;
            color: #7A84A0;
            transition: all 0.2s ease;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #222633;
            color: #B8C2DB;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: #FFFFFF !important;
            color: #0E1117 !important;
            font-weight: 700 !important;
            font-family: 'Fira Code', monospace !important;
            box-shadow: 0 2px 10px rgba(255,255,255,0.15);
        }

        /* ===== INFO / STATUS BOXES ===== */
        .info-box {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-left: 4px solid #FFFFFF;
            border-radius: 0 12px 12px 0;
            padding: 16px 18px;
            margin: 12px 0;
            color: #B8C2DB;
            font-size: 0.88rem;
            line-height: 1.7;
        }
        .warning-box {
            background: #1A1D27;
            border: 1px solid #3A4055;
            border-left: 4px solid #C8CFDF;
            border-radius: 0 12px 12px 0;
            padding: 16px 18px;
            margin: 12px 0;
            color: #B8C2DB;
            font-size: 0.88rem;
            line-height: 1.7;
        }
        .success-box {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-left: 4px solid #FFFFFF;
            border-radius: 0 12px 12px 0;
            padding: 16px 18px;
            margin: 12px 0;
            color: #B8C2DB;
            font-size: 0.88rem;
            line-height: 1.7;
        }
        .danger-box {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-left: 4px solid #7A84A0;
            border-radius: 0 12px 12px 0;
            padding: 16px 18px;
            margin: 12px 0;
            color: #B8C2DB;
            font-size: 0.88rem;
            line-height: 1.7;
        }

        /* ===== SECTION TITLE ===== */
        .section-title {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 28px 0 18px 0;
            padding-bottom: 12px;
            border-bottom: 1px solid #2E3348;
        }
        .section-title-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            font-family: 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', sans-serif;
            color: #F0F4FF;
            flex-shrink: 0;
            opacity: 0.7;
        }
        .section-title-text {
            font-size: 1.15rem;
            font-weight: 600;
            font-family: 'Fira Code', 'Noto Sans Symbols 2', monospace;
            color: #F0F4FF;
            letter-spacing: 0.3px;
        }

        /* ===== TABLE/DATAFRAME ===== */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #2E3348;
        }

        /* ===== DIVIDERS ===== */
        hr {
            border: none;
            height: 1px;
            background: #2E3348;
            margin: 2rem 0;
        }

        /* ===== PLOTLY CHARTS ===== */
        .js-plotly-plot {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid #2E3348;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        }

        /* ===== CUSTOM COLORED METRIC ===== */
        .custom-metric {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 18px 16px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .custom-metric:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.35);
            border-color: #444C66;
        }
        .custom-metric-label {
            color: #7A84A0;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 6px;
        }
        .custom-metric-value {
            font-size: 1.25rem;
            font-weight: 700;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
        }
        /* Card variant dùng cho Monte Carlo metrics */
        .custom-metric-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 8px;
            transition: border-color 0.2s ease;
        }
        .custom-metric-card:hover { border-color: #444C66; }
        .custom-metric-sublabel {
            color: #7A84A0;
            font-size: 0.65rem;
            margin-top: 2px;
        }

        /* ===== EXPANDER ===== */
        .streamlit-expanderHeader {
            font-weight: 600 !important;
            color: #B8C2DB !important;
            font-size: 0.9rem !important;
        }
        details[data-testid="stExpander"] {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            overflow: hidden;
        }

        /* ===== BUTTONS ===== */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            letter-spacing: 0.3px;
        }
        .stDownloadButton > button {
            background: #FFFFFF !important;
            color: #0E1117 !important;
            border: none !important;
            border-radius: 10px;
            font-weight: 700;
            padding: 8px 20px;
            box-shadow: 0 4px 12px rgba(255,255,255,0.12);
            transition: all 0.2s ease;
        }
        .stDownloadButton > button:hover {
            box-shadow: 0 6px 20px rgba(255,255,255,0.2);
            transform: translateY(-1px);
        }

        /* ===== CW COMPARE TAB ===== */
        .cw-compare-header {
            text-align: center;
            font-weight: 700;
            font-size: 1.1rem;
            color: #F0F4FF;
            padding: 12px 8px;
            border-radius: 12px;
            margin-bottom: 14px;
            background: #1A1D27;
            border: 1px solid #2E3348;
        }
        .cw-rank-card {
            text-align: center;
            padding: 14px 10px;
            border-radius: 12px;
            background: #1A1D27;
            border: 1px solid #2E3348;
            margin-bottom: 10px;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .cw-rank-card:hover { transform: translateY(-2px); border-color: #444C66; }
        .cw-rank-card .rank-title {
            font-size: 0.75rem;
            color: #7A84A0;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .cw-rank-card .rank-value { font-size: 1.3rem; font-weight: 700; color: #F0F4FF; }
        .cw-rank-card .rank-detail {
            font-size: 0.75rem;
            color: #7A84A0;
            margin-top: 4px;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
        }

        /* ===== QUICK SUMMARY ===== */
        .quick-summary-signal {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 16px;
            padding: 24px 16px;
            text-align: center;
            min-height: 170px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .signal-score {
            font-size: 3.2rem;
            font-weight: 800;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            line-height: 1;
            margin-bottom: 6px;
            color: #F0F4FF;
        }
        .signal-label {
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 4px;
            color: #F0F4FF;
        }
        .signal-desc {
            font-size: 0.72rem;
            color: #7A84A0;
            line-height: 1.4;
            margin-bottom: 12px;
            max-width: 200px;
        }
        .signal-bar {
            width: 85%;
            height: 6px;
            background: #222633;
            border-radius: 3px;
            overflow: hidden;
        }
        .signal-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
        .quick-summary-signals {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }
        .signal-item {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #222633;
            border: 1px solid #2E3348;
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 0.78rem;
            transition: border-color 0.2s ease;
        }
        .signal-item:hover { border-color: #444C66; }
        .signal-item-icon { font-size: 0.9rem; flex-shrink: 0; }
        .signal-item-label { font-weight: 600; color: #F0F4FF; }
        .signal-item-detail { color: #7A84A0; font-size: 0.72rem; }

        /* ===== SCORE BREAKDOWN CARD ===== */
        .score-card {
            text-align: center;
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            padding: 14px 10px;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .score-card:hover { transform: translateY(-2px); border-color: #444C66; }
        .score-card-label {
            font-size: 0.7rem;
            color: #7A84A0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .score-card-value {
            font-size: 1.3rem;
            font-weight: 700;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            color: #F0F4FF;
        }
        .score-card-bar {
            width: 100%;
            height: 4px;
            background: #222633;
            border-radius: 2px;
            margin-top: 6px;
            overflow: hidden;
        }
        .score-card-bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s ease; }

        /* ===== RECOMMEND BEST CARD ===== */
        .best-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .best-card-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }
        .best-card-score {
            font-size: 3.2rem;
            font-weight: 800;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            line-height: 1;
            color: #F0F4FF;
        }
        .best-card-name { font-size: 1.6rem; font-weight: 700; color: #F0F4FF; }
        .best-card-meta { font-size: 0.85rem; color: #7A84A0; }
        .best-card-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
        }
        .best-card-stat {
            text-align: center;
            background: #222633;
            border: 1px solid #2E3348;
            border-radius: 10px;
            padding: 12px 8px;
        }
        .best-card-stat-label {
            font-size: 0.7rem;
            color: #7A84A0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .best-card-stat-value { font-size: 1.1rem; font-weight: 700; margin-top: 2px; color: #F0F4FF; }

        /* ===== MEDAL CARD (TOP 3) ===== */
        .medal-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .medal-card:hover { transform: translateY(-3px); border-color: #444C66; }
        .medal-card-icon { font-size: 2.2rem; }
        .medal-card-name { font-size: 1.25rem; font-weight: 700; margin: 4px 0; color: #F0F4FF; }
        .medal-card-score {
            font-size: 2rem;
            font-weight: 800;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            margin: 8px 0;
            color: #F0F4FF;
        }
        .medal-card-grade { font-size: 0.8rem; color: #7A84A0; margin-bottom: 10px; }
        .medal-card-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px;
            font-size: 0.78rem;
        }
        .medal-card-grid-label { color: #7A84A0; text-align: right; padding-right: 4px; }
        .medal-card-grid-value { font-weight: 600; color: #B8C2DB; text-align: left; padding-left: 4px; }

        /* ===== FORECAST SCENARIO CARD ===== */
        .scenario-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }
        .scenario-card h4 {
            margin: 0 0 4px 0;
            font-size: 1rem;
            font-weight: 700;
        }
        .scenario-card .subtitle { font-size: 0.8rem; opacity: 0.7; margin-bottom: 12px; }

        /* ===== FOOTER ===== */
        .app-footer {
            text-align: center;
            color: #7A84A0;
            font-size: 0.72rem;
            padding: 24px 0 12px 0;
            border-top: 1px solid #2E3348;
            margin-top: 3rem;
            line-height: 1.6;
        }
        .app-footer a { color: #B8C2DB; text-decoration: none; }

        /* ===== SIDEBAR FILE UPLOADER ===== */
        section[data-testid="stSidebar"] .stFileUploader > div {
            border: 2px dashed #2E3348 !important;
            border-radius: 12px !important;
            transition: border-color 0.2s ease;
        }
        section[data-testid="stSidebar"] .stFileUploader > div:hover {
            border-color: #444C66 !important;
        }

        /* ===== CHART CONTAINER ===== */
        .chart-container {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 16px;
            padding: 20px 16px 12px;
            margin: 12px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        }
        .chart-container-title {
            font-size: 0.78rem;
            font-weight: 600;
            color: #B8C2DB;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 12px;
            padding-left: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .chart-container-title::before {
            content: '';
            width: 3px;
            height: 14px;
            background: #FFFFFF;
            border-radius: 2px;
        }

        /* ===== SECTION DIVIDER ===== */
        .section-divider {
            height: 1px;
            background: #2E3348;
            margin: 1.5rem 0;
            border: none;
        }
        .section-divider-thick {
            height: 2px;
            background: #3A4055;
            margin: 2rem 0;
            border: none;
        }

        /* ===== TAB EMPTY STATE ===== */
        .tab-empty-state {
            text-align: center;
            padding: 60px 20px;
            max-width: 420px;
            margin: 40px auto;
        }
        .tab-empty-state-icon { font-size: 3.5rem; margin-bottom: 16px; opacity: 0.35; font-family: 'Noto Sans Symbols 2', 'Segoe UI Symbol', 'Apple Symbols', sans-serif; }
        .tab-empty-state-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #B8C2DB;
            margin-bottom: 8px;
        }
        .tab-empty-state-text {
            font-size: 0.85rem;
            color: #7A84A0;
            line-height: 1.7;
            margin-bottom: 20px;
        }
        .tab-empty-state-hint {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 10px;
            background: #222633;
            border: 1px solid #2E3348;
            font-size: 0.78rem;
            color: #B8C2DB;
            font-weight: 500;
        }

        /* ===== TABLE CONTAINER ===== */
        .table-container {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 16px;
            margin: 12px 0;
        }
        .table-container-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid #2E3348;
        }
        .table-container-title {
            font-size: 0.78rem;
            font-weight: 600;
            color: #B8C2DB;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }
        .table-container-badge {
            font-size: 0.68rem;
            font-weight: 600;
            color: #7A84A0;
            background: #222633;
            padding: 3px 10px;
            border-radius: 8px;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            border: 1px solid #2E3348;
        }

        /* ===== HEADER v2 ===== */
        .app-header {
            text-align: center;
            padding: 20px 0 16px;
            margin-bottom: 8px;
        }
        .app-header::after {
            content: '';
            display: block;
            width: 80px;
            height: 2px;
            background: #FFFFFF;
            border-radius: 2px;
            margin: 12px auto 0;
        }
        .app-header-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 14px;
            border-radius: 20px;
            background: #222633;
            border: 1px solid #2E3348;
            font-size: 0.65rem;
            font-weight: 600;
            color: #B8C2DB;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        /* ===== FOOTER v2 ===== */
        .app-footer-v2 {
            text-align: center;
            padding: 24px 16px 16px;
            margin-top: 3rem;
        }
        .app-footer-v2-line {
            width: 60px;
            height: 2px;
            background: #2E3348;
            border-radius: 1px;
            margin: 0 auto 16px;
        }
        .app-footer-v2-brand {
            font-size: 0.78rem;
            font-weight: 600;
            color: #7A84A0;
            margin-bottom: 4px;
        }
        .app-footer-v2-disclaimer {
            font-size: 0.68rem;
            color: #5A6278;
            line-height: 1.6;
            max-width: 500px;
            margin: 0 auto;
        }
        .app-footer-v2-designer {
            font-size: 0.68rem;
            color: #444C66;
            margin-top: 8px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }

        /* ===== SCENARIO CARD VARIANTS ===== */
        .scenario-card-bullish {
            background: #1A1D27;
            border: 1px solid #444C66;
        }
        .scenario-card-bearish {
            background: #1A1D27;
            border: 1px solid #2E3348;
        }
        .scenario-card-neutral {
            background: #1A1D27;
            border: 1px solid #3A4055;
        }
        .scenario-card-gold {
            background: #1A1D27;
            border: 1px solid #3A4055;
        }
        .scenario-card-teal {
            background: #1A1D27;
            border: 1px solid #2E3348;
        }

        /* ===== STATUS BADGES ===== */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .status-badge.premium {
            background: #222633;
            color: #B8C2DB;
            border: 1px solid #3A4055;
        }
        .status-badge.discount {
            background: #222633;
            color: #F0F4FF;
            border: 1px solid #444C66;
        }
        .status-badge.fair {
            background: #1A1D27;
            color: #7A84A0;
            border: 1px solid #2E3348;
        }

        /* ===== BATCH STATS GRID ===== */
        .batch-stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin: 16px 0;
        }
        .batch-stat-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 16px 12px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .batch-stat-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            border-radius: 14px 14px 0 0;
        }
        .batch-stat-card.total::before       { background: #FFFFFF; }
        .batch-stat-card.bsc-discount::before { background: #C8CFDF; }
        .batch-stat-card.bsc-premium::before  { background: #7A84A0; }
        .batch-stat-card.bsc-fair::before     { background: #B8C2DB; }
        .batch-stat-card-value {
            font-size: 1.8rem;
            font-weight: 800;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            line-height: 1;
            margin-bottom: 4px;
            color: #F0F4FF;
        }
        .batch-stat-card-label {
            font-size: 0.7rem;
            font-weight: 600;
            color: #7A84A0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* ===== DAILY TRACKER ===== */
        .daily-input-form {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-left: 3px solid #FFFFFF;
            border-radius: 14px;
            padding: 16px;
            margin: 12px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        }
        .trend-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .trend-badge.up {
            background: #222633;
            color: #F0F4FF;
            border: 1px solid #444C66;
        }
        .trend-badge.down {
            background: #1A1D27;
            color: #7A84A0;
            border: 1px solid #2E3348;
        }
        .trend-badge.flat {
            background: #1A1D27;
            color: #B8C2DB;
            border: 1px solid #3A4055;
        }
        .data-source-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .data-source-badge.real {
            background: #222633;
            color: #F0F4FF;
            border: 1px solid #444C66;
        }
        .data-source-badge.estimated {
            background: #1A1D27;
            color: #B8C2DB;
            border: 1px solid #3A4055;
        }
        .daily-stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin: 20px 0;
        }
        .daily-stat-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 14px;
            padding: 16px 12px;
            text-align: center;
        }
        .daily-stat-card-value {
            font-size: 1.3rem;
            font-weight: 800;
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            line-height: 1.2;
            margin-bottom: 6px;
            color: #F0F4FF;
        }
        .daily-stat-card-label {
            font-size: 0.70rem;
            font-weight: 600;
            color: #7A84A0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            line-height: 1.4;
        }

        /* ===== HEDGING TAB ===== */

        /* Risk profile cards (5 horizontal) */
        .rp-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin: 12px 0 20px 0;
        }
        .rp-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            padding: 14px 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
        }
        .rp-card:hover { border-color: #444C66; background: #222633; }
        .rp-card.rp-selected {
            border-color: #FFFFFF;
            border-width: 2px;
            background: #222633;
            box-shadow: 0 0 15px rgba(255,255,255,0.08);
        }
        .rp-icon {
            font-size: 1.6rem;
            margin-bottom: 4px;
            font-family: 'Fira Code', monospace;
            font-weight: 700;
        }
        .rp-name {
            font-family: 'Fira Code', monospace;
            font-size: 0.82rem;
            font-weight: 600;
            color: #F0F4FF;
            margin-bottom: 4px;
        }
        .rp-desc {
            font-size: 0.7rem;
            color: #7A84A0;
            line-height: 1.4;
            margin-bottom: 6px;
        }
        .rp-target {
            font-family: 'Fira Code', monospace;
            font-size: 0.68rem;
            color: #B8C2DB;
            padding: 3px 6px;
            background: rgba(255,255,255,0.04);
            border-radius: 4px;
            display: inline-block;
        }

        /* Stock position mini-cards */
        .stock-pos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 8px;
            margin: 10px 0;
        }
        .stock-pos-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 10px;
            padding: 12px;
        }
        .stock-pos-ticker {
            font-family: 'Fira Code', monospace;
            font-weight: 700;
            font-size: 1rem;
            color: #F0F4FF;
        }
        .stock-pos-detail {
            font-size: 0.78rem;
            color: #7A84A0;
            margin-top: 4px;
        }
        .stock-pos-pnl {
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 6px;
        }

        /* Strategy section cards */
        .strategy-card {
            background: #1A1D27;
            border: 1px solid #2E3348;
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
        }
        .strategy-card-title {
            font-family: 'Fira Code', monospace;
            font-size: 0.95rem;
            font-weight: 600;
            color: #F0F4FF;
            margin-bottom: 10px;
        }

        /* Delta gauge indicator */
        .delta-gauge {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 8px 0;
        }
        .delta-gauge-bar {
            flex: 1;
            height: 8px;
            background: #2E3348;
            border-radius: 4px;
            position: relative;
            overflow: visible;
        }
        .delta-gauge-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .delta-gauge-label {
            font-family: 'Fira Code', monospace;
            font-size: 0.78rem;
            color: #B8C2DB;
            white-space: nowrap;
        }

        @media (max-width: 1024px) {
            .rp-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 768px) {
            .rp-grid { grid-template-columns: repeat(2, 1fr); }
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 1024px) {
            .daily-stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 768px) {
            .main-header { font-size: 1.4rem; letter-spacing: 1.5px; }
            .best-card-grid { grid-template-columns: repeat(2, 1fr); }
            .medal-card-grid { font-size: 0.7rem; }
            .batch-stats-grid { grid-template-columns: repeat(2, 1fr); }
            .daily-stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Tab scroll arrows ──
    st.markdown("""
    <script>
    (function() {
        function injectArrows() {
            const tabList = document.querySelector('[data-baseweb="tab-list"]');
            if (!tabList || tabList.dataset.arrowsInjected) return;
            tabList.dataset.arrowsInjected = '1';

            const wrapper = tabList.parentElement;
            wrapper.style.position = 'relative';

            const arrowStyle = `
                position: absolute; top: 50%; transform: translateY(-50%);
                width: 28px; height: 28px; border-radius: 50%;
                background: #1A1D27; border: 1px solid #444C66;
                color: #B8C2DB; font-size: 14px; cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                z-index: 10; transition: all 0.2s ease;
                font-family: 'Noto Sans Symbols 2', sans-serif;
            `;

            const leftBtn = document.createElement('button');
            leftBtn.innerHTML = '‹';
            leftBtn.style.cssText = arrowStyle + 'left: 4px;';
            leftBtn.onmouseover = () => { leftBtn.style.background = '#2E3348'; leftBtn.style.color = '#F0F4FF'; };
            leftBtn.onmouseout  = () => { leftBtn.style.background = '#1A1D27'; leftBtn.style.color = '#B8C2DB'; };
            leftBtn.onclick = () => tabList.scrollBy({ left: -200, behavior: 'smooth' });

            const rightBtn = document.createElement('button');
            rightBtn.innerHTML = '›';
            rightBtn.style.cssText = arrowStyle + 'right: 4px;';
            rightBtn.onmouseover = () => { rightBtn.style.background = '#2E3348'; rightBtn.style.color = '#F0F4FF'; };
            rightBtn.onmouseout  = () => { rightBtn.style.background = '#1A1D27'; rightBtn.style.color = '#B8C2DB'; };
            rightBtn.onclick = () => tabList.scrollBy({ left: 200, behavior: 'smooth' });

            wrapper.appendChild(leftBtn);
            wrapper.appendChild(rightBtn);
        }

        // Retry until Streamlit tabs render
        let attempts = 0;
        const interval = setInterval(() => {
            injectArrows();
            attempts++;
            if (document.querySelector('[data-baseweb="tab-list"][data-arrows-injected]') || attempts > 30) {
                clearInterval(interval);
            }
        }, 300);
    })();
    </script>
    """, unsafe_allow_html=True)
