"""
Mô Phỏng Monte Carlo cho Danh Mục Chứng Quyền.

Thuật toán:
1. Gom CW theo cổ phiếu cơ sở → mỗi underlying có 1 GBM path duy nhất
2. Cholesky decomposition để tạo correlated random shocks
3. GBM daily steps: S(t+dt) = S(t) × exp((r - q - σ²/2)×dt + σ×√dt×Z)
4. Reprice mỗi CW tại mỗi bước dùng BlackScholesModel
5. Tính PnL danh mục: Σ (CW_price_T - entry_price) × quantity
"""

import numpy as np
from core.black_scholes import BlackScholesModel


# ============================================================
# PUBLIC API
# ============================================================

def simulate_portfolio(
    portfolio: list[dict],
    n_paths: int = 5_000,
    holding_days: int = 30,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    Chạy Monte Carlo simulation cho toàn bộ danh mục CW.

    Parameters
    ----------
    portfolio : list[dict]
        Danh sách CW từ st.session_state["cw_portfolio"].
        Mỗi CW có: S, K, T, r, sigma, q, cr, cw_price, option_type,
                   ma_co_so, ma_cw, quantity (optional), entry_price (optional).
    n_paths : int
        Số lượng paths mô phỏng.
    holding_days : int
        Số ngày giữ danh mục.
    confidence_level : float
        Độ tin cậy VaR (0.90, 0.95, 0.99).
    seed : int | None
        Random seed để tái tạo kết quả.

    Returns
    -------
    dict với các keys:
        days          : np.ndarray [holding_days+1]
        port_paths    : np.ndarray [n_paths, holding_days+1]  (giá trị danh mục)
        pnl_final     : np.ndarray [n_paths]                  (PnL cuối kỳ)
        pnl_baseline  : float                                 (PnL nếu giá không đổi)
        per_cw        : list[dict]  (per-CW stats)
        stats         : dict        (VaR, CVaR, mean, ...)
        included_cw   : list[str]   (tên CW đưa vào simulation)
        fallback_mode : bool        (True nếu không có vị thế → dùng 1 unit mặc định)
        n_paths       : int
        holding_days  : int
    """
    if seed is not None:
        np.random.seed(seed)

    # Chuẩn bị: xác định CW tham gia và chế độ tính PnL
    cw_list, fallback_mode = _prepare_cw_list(portfolio)

    if not cw_list:
        return _empty_result(n_paths, holding_days)

    n_steps = holding_days  # 1 step = 1 ngày
    dt = 1.0 / 252.0       # Daily step (252 ngày giao dịch/năm)

    # ── Gom nhóm CW theo underlying ──────────────────────────
    underlying_map = _build_underlying_map(cw_list)
    underlyings = list(underlying_map.keys())
    n_underlying = len(underlyings)

    # ── Tham số GBM cho từng underlying ──────────────────────
    # Lấy sigma, r, q từ CW đầu tiên trong nhóm (cùng cổ phiếu)
    gbm_params = {}
    for ux in underlyings:
        idx0 = underlying_map[ux][0]
        cw0 = cw_list[idx0]
        gbm_params[ux] = {
            "S0":    cw0["S"],
            "sigma": cw0["sigma"],
            "r":     cw0["r"],
            "q":     cw0.get("q", 0.0),
        }

    # ── Correlation matrix cho underlyings ───────────────────
    corr = _underlying_corr(underlyings)

    # ── Cholesky decomposition ────────────────────────────────
    # Đảm bảo PSD bằng cách thêm epsilon nhỏ vào diagonal
    corr_psd = corr + np.eye(n_underlying) * 1e-8
    L = np.linalg.cholesky(corr_psd)   # [n_underlying, n_underlying]

    # ── Sinh paths GBM có tương quan ─────────────────────────
    # S_paths[u, p, t] = giá underlying u tại path p, bước t
    S_paths = np.zeros((n_underlying, n_paths, n_steps + 1))
    for u, ux in enumerate(underlyings):
        S_paths[u, :, 0] = gbm_params[ux]["S0"]

    for t in range(1, n_steps + 1):
        # eps[n_underlying, n_paths] ~ N(0,I)
        eps = np.random.standard_normal((n_underlying, n_paths))
        # Z = L @ eps → correlated shocks [n_underlying, n_paths]
        Z = L @ eps

        for u, ux in enumerate(underlyings):
            p = gbm_params[ux]
            drift = (p["r"] - p["q"] - 0.5 * p["sigma"] ** 2) * dt
            diffusion = p["sigma"] * np.sqrt(dt) * Z[u]
            S_paths[u, :, t] = S_paths[u, :, t - 1] * np.exp(drift + diffusion)

    # ── Định giá CW tại mỗi bước ─────────────────────────────
    # cw_value_paths[i, p, t] = giá CW i tại path p, bước t
    n_cw = len(cw_list)
    cw_value_paths = np.zeros((n_cw, n_paths, n_steps + 1))

    # Chỉ số underlying cho từng CW
    ux_index = {ux: u for u, ux in enumerate(underlyings)}

    for i, cw in enumerate(cw_list):
        u = ux_index[cw["ma_co_so"]]
        K = cw["K"]
        T_orig = cw["T"]
        r = cw["r"]
        sigma = cw["sigma"]
        q = cw.get("q", 0.0)
        cr = cw["cr"]
        opt_type = cw["option_type"]

        # Giá CW tại t=0 (giá thực tế hiện tại)
        cw_value_paths[i, :, 0] = cw["entry_price"]

        for t in range(1, n_steps + 1):
            T_rem = max(T_orig - t / 252.0, 0.0)
            S_t = S_paths[u, :, t]   # [n_paths]

            # Vectorized repricing — batch bằng numpy
            cw_prices_t = _batch_bs_price(S_t, K, T_rem, r, sigma, opt_type, q, cr)
            cw_value_paths[i, :, t] = cw_prices_t

    # ── Tính PnL danh mục ─────────────────────────────────────
    # port_pnl_paths[p, t] = tổng PnL tại path p, bước t
    port_pnl_paths = np.zeros((n_paths, n_steps + 1))
    for i, cw in enumerate(cw_list):
        qty = cw["quantity"]
        entry = cw["entry_price"]
        # PnL = (giá hiện tại - giá vào) × số lượng
        pnl_i = (cw_value_paths[i] - entry) * qty   # [n_paths, n_steps+1]
        port_pnl_paths += pnl_i

    pnl_final = port_pnl_paths[:, -1]  # [n_paths]

    # Baseline: PnL nếu giá không đổi (giá CW giữ nguyên)
    pnl_baseline = _compute_baseline_pnl(cw_list, holding_days)

    # ── Percentile paths ─────────────────────────────────────
    pcts = [5, 25, 50, 75, 95]
    percentiles = {
        f"p{p}": np.percentile(port_pnl_paths, p, axis=0)
        for p in pcts
    }

    # ── Statistics ───────────────────────────────────────────
    stats = _compute_stats(pnl_final, pnl_baseline, confidence_level)

    # ── Per-CW stats ──────────────────────────────────────────
    per_cw = []
    for i, cw in enumerate(cw_list):
        qty = cw["quantity"]
        entry = cw["entry_price"]
        pnl_i_final = (cw_value_paths[i, :, -1] - entry) * qty
        per_cw.append({
            "ma_cw":         cw.get("ma_cw", f"CW #{i}"),
            "ma_co_so":      cw.get("ma_co_so", "N/A"),
            "quantity":      qty,
            "entry_price":   entry,
            "current_price": cw["cw_price"],
            "expected_pnl":  float(np.mean(pnl_i_final)),
            "std_pnl":       float(np.std(pnl_i_final)),
            "prob_profit":   float(np.mean(pnl_i_final > 0)),
        })

    days = np.arange(n_steps + 1)

    return {
        "days":           days,
        "port_paths":     port_pnl_paths,
        "percentiles":    percentiles,
        "pnl_final":      pnl_final,
        "pnl_baseline":   pnl_baseline,
        "per_cw":         per_cw,
        "stats":          stats,
        "included_cw":    [cw.get("ma_cw", f"CW #{i}") for i, cw in enumerate(cw_list)],
        "fallback_mode":  fallback_mode,
        "n_paths":        n_paths,
        "holding_days":   holding_days,
        "confidence_level": confidence_level,
    }


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _prepare_cw_list(portfolio: list[dict]) -> tuple[list[dict], bool]:
    """
    Lọc CW có vị thế (quantity + entry_price).
    Nếu không có → fallback mode: dùng 1 unit với entry_price = cw_price.

    Returns (cw_list, fallback_mode).
    """
    has_position = [
        cw for cw in portfolio
        if cw.get("quantity") and cw.get("entry_price")
        and cw["quantity"] > 0 and cw["entry_price"] > 0
    ]

    if has_position:
        return has_position, False

    # Fallback: dùng tất cả CW, 1 unit mỗi CW, entry = giá hiện tại
    fallback = []
    for cw in portfolio:
        cw_copy = dict(cw)
        cw_copy["quantity"] = 1
        cw_copy["entry_price"] = cw["cw_price"]
        fallback.append(cw_copy)

    return fallback, True


def _build_underlying_map(cw_list: list[dict]) -> dict[str, list[int]]:
    """
    Gom CW theo underlying: {ma_co_so → [idx1, idx2, ...]}.
    """
    mapping: dict[str, list[int]] = {}
    for i, cw in enumerate(cw_list):
        ux = cw.get("ma_co_so", "UNKNOWN")
        mapping.setdefault(ux, []).append(i)
    return mapping


def _underlying_corr(underlyings: list[str]) -> np.ndarray:
    """
    Correlation matrix giữa các underlying stocks.
    Khác nhau → ρ = 0.30 (thị trường VN tương quan dương nhẹ).
    """
    n = len(underlyings)
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            rho = 0.30  # Khác underlying → tương quan dương 30%
            corr[i, j] = rho
            corr[j, i] = rho
    return corr


def _batch_bs_price(
    S_arr: np.ndarray,
    K: float, T: float, r: float, sigma: float,
    option_type: str, q: float, cr: float,
) -> np.ndarray:
    """
    Vectorized Black-Scholes pricing cho mảng giá S.
    Dùng công thức trực tiếp thay vì vòng lặp để tối ưu tốc độ.
    """
    from scipy.stats import norm

    if T <= 0 or sigma <= 0:
        # Intrinsic value
        if option_type == "call":
            intrinsic = np.maximum(0.0, S_arr - K)
        else:
            intrinsic = np.maximum(0.0, K - S_arr)
        return intrinsic / cr

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S_arr / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    discount_r = np.exp(-r * T)
    discount_q = np.exp(-q * T)

    if option_type == "call":
        price = S_arr * discount_q * norm.cdf(d1) - K * discount_r * norm.cdf(d2)
    else:
        price = K * discount_r * norm.cdf(-d2) - S_arr * discount_q * norm.cdf(-d1)

    return np.maximum(price, 0.0) / cr


def _compute_baseline_pnl(cw_list: list[dict], holding_days: int) -> float:
    """
    PnL nếu giá cơ sở không đổi (chỉ time decay).
    Reprice mỗi CW với S giữ nguyên, T giảm đi holding_days.
    """
    total = 0.0
    for cw in cw_list:
        T_rem = max(cw["T"] - holding_days / 252.0, 0.0)
        bs = BlackScholesModel(
            S=cw["S"], K=cw["K"], T=T_rem,
            r=cw["r"], sigma=cw["sigma"],
            option_type=cw["option_type"],
            q=cw.get("q", 0.0),
        )
        new_price = bs.warrant_price(cw["cr"])
        pnl = (new_price - cw["entry_price"]) * cw["quantity"]
        total += pnl
    return total


def _compute_stats(
    pnl_final: np.ndarray,
    pnl_baseline: float,
    confidence_level: float,
) -> dict:
    """
    Tính các metrics rủi ro từ phân phối PnL cuối kỳ.
    """
    alpha = 1.0 - confidence_level  # VaR tail probability

    var_level  = float(np.percentile(pnl_final, alpha * 100))
    cvar_level = float(np.mean(pnl_final[pnl_final <= var_level]))

    # Luôn tính thêm VaR 95% và 99% để hiển thị trên chart
    var_95 = float(np.percentile(pnl_final, 5))
    var_99 = float(np.percentile(pnl_final, 1))
    cvar_95 = float(np.mean(pnl_final[pnl_final <= var_95]))

    return {
        "mean":          float(np.mean(pnl_final)),
        "std":           float(np.std(pnl_final)),
        "median":        float(np.median(pnl_final)),
        "var":           var_level,           # VaR tại confidence đã chọn
        "cvar":          cvar_level,          # CVaR tại confidence đã chọn
        "var_95":        var_95,
        "var_99":        var_99,
        "cvar_95":       cvar_95,
        "max_gain":      float(np.percentile(pnl_final, 99)),
        "max_loss":      float(np.percentile(pnl_final, 1)),
        "prob_profit":   float(np.mean(pnl_final > 0)),
        "pnl_baseline":  pnl_baseline,
        "confidence_level": confidence_level,
    }


def _empty_result(n_paths: int, holding_days: int) -> dict:
    """Trả về kết quả rỗng khi portfolio không có CW hợp lệ."""
    return {
        "days":           np.arange(holding_days + 1),
        "port_paths":     np.zeros((n_paths, holding_days + 1)),
        "percentiles":    {f"p{p}": np.zeros(holding_days + 1) for p in [5, 25, 50, 75, 95]},
        "pnl_final":      np.zeros(n_paths),
        "pnl_baseline":   0.0,
        "per_cw":         [],
        "stats":          _compute_stats(np.zeros(n_paths), 0.0, 0.95),
        "included_cw":    [],
        "fallback_mode":  False,
        "n_paths":        n_paths,
        "holding_days":   holding_days,
        "confidence_level": 0.95,
    }
