"""
Markowitz Mean-Variance Portfolio Optimization cho Chứng Quyền.

Vì CW không có dữ liệu lịch sử (historical returns), module này
ước tính Expected Return & Risk từ mô hình Black-Scholes:

- Expected Return (μ): Dựa trên effective leverage × scenario analysis
- Risk (σ_port):       Dựa trên implied/input volatility × leverage
- Correlation:         Proxy từ cùng/khác cổ phiếu cơ sở

Tối ưu hoá bằng phương pháp Quadratic Programming (hoặc grid search
nếu numpy-only) để tìm danh mục Sharpe Ratio tối đa.
"""
import numpy as np
from dataclasses import dataclass


@dataclass
class CWAsset:
    """Thông tin tài sản CW cho Markowitz."""
    name: str
    expected_return: float      # Kỳ vọng lợi nhuận (decimal, e.g. 0.15 = 15%)
    volatility: float           # Rủi ro (std dev of return, decimal)
    cw_price: float             # Giá CW hiện tại
    ma_co_so: str               # Mã cổ phiếu cơ sở (dùng tính correlation)
    option_type: str            # "call" / "put"
    score: int                  # Điểm đánh giá (0-100)


def estimate_cw_return(analysis: dict, cw_input: dict) -> float:
    """
    Ước tính expected return cho CW dựa trên Black-Scholes.

    Logic cải tiến:
    - Convergence return: khoảng cách giá LT vs giá TT (trọng số chính)
    - Leverage return: chỉ cộng khi CW đang Discount hoặc ATM
    - Premium penalty: CW đang Premium cao → expected return bị phạt nặng
    - Time decay penalty: CW gần đáo hạn bị giảm kỳ vọng
    - Score weighting: CW điểm thấp bị giảm expected return
    """
    pd_info = analysis["premium_discount"]
    theo_price = analysis["theoretical_price"]
    market_price = pd_info["market_price"]
    eff_lev = analysis["effective_leverage"]
    pd_pct = pd_info["percentage"]  # Premium/Discount %

    if market_price <= 0:
        return 0.0

    # 1. Convergence return: khoảng cách giữa giá LT và giá TT
    #    Đây là phần "chắc chắn" nhất — nếu giá TT > giá LT → CW đang đắt
    convergence_return = (theo_price - market_price) / market_price

    # 2. Leverage-adjusted base return
    equity_premium = 0.08
    T = cw_input.get("T", 0.5)
    base_stock_return = equity_premium * min(T, 1.0)
    leverage_return = base_stock_return * eff_lev

    # Put warrants: expected return ngược chiều
    if cw_input["option_type"] == "put":
        leverage_return = -leverage_return

    # 3. Kết hợp — tăng trọng số convergence, giảm leverage
    #    CW đang Premium → convergence âm → nên chiếm trọng số lớn hơn
    if pd_pct > 5:
        # Premium > 5%: convergence chiếm 80%, leverage chỉ 20%
        # Vì CW đang đắt → khó có lời từ leverage
        expected_return = 0.80 * convergence_return + 0.20 * leverage_return
    elif pd_pct > 0:
        # Premium nhẹ (0-5%): 70% / 30%
        expected_return = 0.70 * convergence_return + 0.30 * leverage_return
    else:
        # Discount: 55% convergence + 45% leverage (CW đang rẻ, leverage có ý nghĩa)
        expected_return = 0.55 * convergence_return + 0.45 * leverage_return

    # 4. Time decay penalty — CW gần đáo hạn mất giá trị nhanh
    days = cw_input.get("days_remaining", int(T * 365))
    if days < 30:
        expected_return -= 0.15  # -15% penalty cho CW < 30 ngày
    elif days < 60:
        expected_return -= 0.05  # -5% penalty cho CW < 60 ngày

    # 5. Premium penalty bổ sung — CW Premium cao bị phạt thêm
    #    Vì CW Premium cao rất khó hoà vốn
    if pd_pct > 20:
        expected_return -= 0.10  # -10% thêm nếu Premium > 20%
    elif pd_pct > 10:
        expected_return -= 0.05  # -5% thêm nếu Premium > 10%

    return expected_return


def estimate_cw_volatility(analysis: dict, cw_input: dict) -> float:
    """
    Ước tính volatility (standard deviation of return) cho CW.

    CW volatility ≈ underlying volatility × effective leverage.
    Điều chỉnh thêm theo thời gian còn lại.
    """
    sigma = cw_input.get("sigma", 0.30)
    iv = analysis.get("implied_volatility")
    eff_lev = max(analysis["effective_leverage"], 0.1)
    T = cw_input.get("T", 0.5)

    # Dùng max(IV, input sigma) để conservative hơn
    base_vol = max(iv, sigma) if iv else sigma

    # CW vol ≈ base_vol × leverage, scaled by sqrt(T) cho holding period
    cw_vol = base_vol * eff_lev * min(np.sqrt(T), 1.0)

    # Floor & cap
    cw_vol = max(0.05, min(cw_vol, 5.0))

    return cw_vol


def build_correlation_matrix(assets: list[CWAsset]) -> np.ndarray:
    """
    Xây dựng correlation matrix proxy cho các CW.

    Rules:
    - Cùng cổ phiếu cơ sở, cùng loại (call/call): ρ = 0.90
    - Cùng cổ phiếu cơ sở, khác loại (call/put): ρ = -0.70
    - Khác cổ phiếu cơ sở: ρ = 0.30 (market correlation)
    - Khác cổ phiếu cơ sở, khác loại: ρ = -0.10
    """
    n = len(assets)
    corr = np.eye(n)

    for i in range(n):
        for j in range(i + 1, n):
            same_stock = (assets[i].ma_co_so == assets[j].ma_co_so)
            same_type = (assets[i].option_type == assets[j].option_type)

            if same_stock and same_type:
                rho = 0.90
            elif same_stock and not same_type:
                rho = -0.70
            elif not same_stock and same_type:
                rho = 0.30
            elif not same_stock and not same_type:
                rho = -0.10
            else:
                rho = 0.20

            corr[i, j] = rho
            corr[j, i] = rho

    return corr


def build_covariance_matrix(assets: list[CWAsset], corr: np.ndarray) -> np.ndarray:
    """Chuyển correlation matrix → covariance matrix."""
    n = len(assets)
    vols = np.array([a.volatility for a in assets])
    cov = np.outer(vols, vols) * corr
    return cov


def portfolio_metrics(weights: np.ndarray, returns: np.ndarray,
                      cov_matrix: np.ndarray) -> tuple[float, float, float]:
    """
    Tính expected return, volatility, và Sharpe ratio của portfolio.
    Returns: (port_return, port_vol, sharpe)
    """
    port_return = np.dot(weights, returns)
    port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
    risk_free = 0.03  # 3% risk-free rate
    sharpe = (port_return - risk_free) / port_vol if port_vol > 1e-10 else 0.0
    return port_return, port_vol, sharpe


def optimize_max_sharpe(assets: list[CWAsset], corr: np.ndarray,
                        n_points: int = 20000) -> np.ndarray:
    """
    Tìm portfolio Sharpe Ratio tối đa bằng Monte Carlo simulation.

    Dùng phương pháp random search (không cần scipy) — đủ chính xác
    cho portfolio nhỏ (2-15 CW).

    Returns: optimal weights array (sum = 1, each >= 0)
    """
    n = len(assets)
    returns = np.array([a.expected_return for a in assets])
    cov = build_covariance_matrix(assets, corr)

    best_sharpe = -999
    best_weights = np.ones(n) / n  # fallback: equal weight

    # Monte Carlo random portfolios
    for _ in range(n_points):
        # Random weights (Dirichlet distribution → sum = 1, all >= 0)
        w = np.random.dirichlet(np.ones(n))

        _, _, sharpe = portfolio_metrics(w, returns, cov)

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_weights = w.copy()

    return best_weights


def optimize_min_variance(assets: list[CWAsset], corr: np.ndarray,
                          n_points: int = 20000) -> np.ndarray:
    """
    Tìm portfolio Minimum Variance bằng Monte Carlo simulation.
    Returns: optimal weights array
    """
    n = len(assets)
    returns = np.array([a.expected_return for a in assets])
    cov = build_covariance_matrix(assets, corr)

    best_vol = 999
    best_weights = np.ones(n) / n

    for _ in range(n_points):
        w = np.random.dirichlet(np.ones(n))
        _, port_vol, _ = portfolio_metrics(w, returns, cov)

        if port_vol < best_vol:
            best_vol = port_vol
            best_weights = w.copy()

    return best_weights


def generate_efficient_frontier(assets: list[CWAsset], corr: np.ndarray,
                                n_portfolios: int = 5000) -> dict:
    """
    Tạo dữ liệu Efficient Frontier bằng Monte Carlo simulation.

    Returns dict:
    {
        "returns": np.ndarray,     # Expected returns of random portfolios
        "volatilities": np.ndarray, # Volatilities
        "sharpes": np.ndarray,      # Sharpe ratios
        "weights": list[np.ndarray], # Weight arrays
        "max_sharpe_idx": int,       # Index of max Sharpe portfolio
        "min_vol_idx": int,          # Index of min variance portfolio
    }
    """
    n = len(assets)
    returns_arr = np.array([a.expected_return for a in assets])
    cov = build_covariance_matrix(assets, corr)

    port_returns = np.zeros(n_portfolios)
    port_vols = np.zeros(n_portfolios)
    port_sharpes = np.zeros(n_portfolios)
    port_weights = []

    for i in range(n_portfolios):
        w = np.random.dirichlet(np.ones(n))
        ret, vol, sharpe = portfolio_metrics(w, returns_arr, cov)
        port_returns[i] = ret
        port_vols[i] = vol
        port_sharpes[i] = sharpe
        port_weights.append(w)

    return {
        "returns": port_returns,
        "volatilities": port_vols,
        "sharpes": port_sharpes,
        "weights": port_weights,
        "max_sharpe_idx": int(np.argmax(port_sharpes)),
        "min_vol_idx": int(np.argmin(port_vols)),
    }


# ============================================================
# HISTORICAL DATA SUPPORT (Daily Tracker integration)
# ============================================================

def get_historical_params(ma_cw: str, min_points: int = 5):
    """
    Tính actual return + volatility từ daily history.

    Returns None nếu < min_points records.
    Returns dict {"expected_return", "volatility", "n_points", "returns_series"}
    nếu đủ data.

    Annualization: 252 trading days/year.
    """
    try:
        from data.daily_tracker import compute_daily_returns
    except ImportError:
        return None

    returns = compute_daily_returns(ma_cw)
    if returns is None or len(returns) < min_points:
        return None

    mean_daily = np.mean(returns)
    std_daily = np.std(returns, ddof=1)

    # Annualize
    annual_return = mean_daily * 252
    annual_vol = std_daily * np.sqrt(252)

    # Floor & cap giống estimate functions
    annual_vol = max(0.05, min(annual_vol, 5.0))

    return {
        "expected_return": annual_return,
        "volatility": annual_vol,
        "n_points": len(returns),
        "returns_series": returns,
    }


def _proxy_correlation(a1: CWAsset, a2: CWAsset) -> float:
    """Tính proxy correlation giữa 2 CW dựa trên rules."""
    same_stock = (a1.ma_co_so == a2.ma_co_so)
    same_type = (a1.option_type == a2.option_type)

    if same_stock and same_type:
        return 0.90
    elif same_stock and not same_type:
        return -0.70
    elif not same_stock and same_type:
        return 0.30
    else:
        return -0.10


def build_historical_correlation_matrix(
    assets: list,
    history_returns_map: dict,
    min_overlap: int = 5,
) -> np.ndarray:
    """
    Build correlation matrix dùng actual returns khi có.
    Fallback to proxy rules cho pairs thiếu data.

    Args:
        assets: list of CWAsset
        history_returns_map: {cw_name: np.ndarray of returns}
        min_overlap: Số điểm overlap tối thiểu để dùng actual correlation
    """
    n = len(assets)
    corr = np.eye(n)

    for i in range(n):
        for j in range(i + 1, n):
            ri = history_returns_map.get(assets[i].name)
            rj = history_returns_map.get(assets[j].name)

            if ri is not None and rj is not None:
                # Align by truncating to min length
                min_len = min(len(ri), len(rj))
                if min_len >= min_overlap:
                    rho = np.corrcoef(ri[-min_len:], rj[-min_len:])[0, 1]
                    # Handle NaN
                    if np.isnan(rho):
                        rho = _proxy_correlation(assets[i], assets[j])
                    else:
                        rho = max(-0.99, min(0.99, rho))
                    corr[i, j] = rho
                    corr[j, i] = rho
                    continue

            # Fallback to proxy
            rho = _proxy_correlation(assets[i], assets[j])
            corr[i, j] = rho
            corr[j, i] = rho

    return corr


def run_markowitz(results: list[dict], use_history: bool = True) -> dict:
    """
    Entry point chính — nhận results từ tab_recommend và trả về
    kết quả Markowitz optimization.

    Cải tiến: Lọc bỏ CW có expected return quá âm (< -5%) trước khi
    tối ưu hoá, vì không hợp lý phân bổ tiền cho CW chắc chắn lỗ.

    Parameters:
        results: list of {"name", "input", "analysis", "score", "breakdown"}
                 (đã sorted theo score)

    Returns dict:
    {
        "assets": list[CWAsset],           # CW tham gia tối ưu
        "excluded_assets": list[CWAsset],   # CW bị loại (return quá âm)
        "corr_matrix": np.ndarray,
        "cov_matrix": np.ndarray,
        "max_sharpe_weights": np.ndarray,
        "min_var_weights": np.ndarray,
        "max_sharpe_metrics": (return, vol, sharpe),
        "min_var_metrics": (return, vol, sharpe),
        "frontier": dict (from generate_efficient_frontier),
        "included_indices": list[int],      # Index trong results[] cho CW tham gia
        "excluded_indices": list[int],      # Index trong results[] cho CW bị loại
    }
    """
    MIN_RETURN_THRESHOLD = -0.05  # Loại CW có expected return < -5%

    # 1. Xây dựng CWAsset list — dùng historical data khi có
    all_assets = []
    data_sources = {}         # {cw_name: "real" | "estimated"}
    history_returns_map = {}  # {cw_name: np.ndarray} cho correlation

    for r in results:
        cw_input = r["input"]
        analysis = r["analysis"]
        ma_cw = r["name"]

        # Thử lấy historical params nếu use_history=True
        hist_params = None
        if use_history:
            hist_params = get_historical_params(ma_cw)

        if hist_params is not None:
            exp_ret = hist_params["expected_return"]
            vol = hist_params["volatility"]
            history_returns_map[ma_cw] = hist_params["returns_series"]
            data_sources[ma_cw] = "real"
        else:
            exp_ret = estimate_cw_return(analysis, cw_input)
            vol = estimate_cw_volatility(analysis, cw_input)
            data_sources[ma_cw] = "estimated"

        all_assets.append(CWAsset(
            name=ma_cw,
            expected_return=exp_ret,
            volatility=vol,
            cw_price=cw_input["cw_price"],
            ma_co_so=cw_input.get("ma_co_so", "N/A"),
            option_type=cw_input["option_type"],
            score=r["score"],
        ))

    # 2. Lọc: loại CW có expected return quá âm
    included_indices = []
    excluded_indices = []
    assets = []
    excluded_assets = []

    for i, asset in enumerate(all_assets):
        if asset.expected_return >= MIN_RETURN_THRESHOLD:
            included_indices.append(i)
            assets.append(asset)
        else:
            excluded_indices.append(i)
            excluded_assets.append(asset)

    # Nếu lọc hết → giữ lại CW có return cao nhất
    if len(assets) < 2:
        # Sắp xếp theo expected return giảm dần, giữ ít nhất 2
        sorted_indices = sorted(range(len(all_assets)),
                                key=lambda i: all_assets[i].expected_return,
                                reverse=True)
        assets = []
        excluded_assets = []
        included_indices = []
        excluded_indices = []
        for idx in sorted_indices[:max(2, len(all_assets))]:
            included_indices.append(idx)
            assets.append(all_assets[idx])
        for idx in sorted_indices[max(2, len(all_assets)):]:
            excluded_indices.append(idx)
            excluded_assets.append(all_assets[idx])

    # 3. Correlation & Covariance (chỉ cho assets tham gia)
    #    Dùng historical correlation nếu có data, fallback to proxy
    if use_history and history_returns_map:
        corr = build_historical_correlation_matrix(assets, history_returns_map)
    else:
        corr = build_correlation_matrix(assets)
    cov = build_covariance_matrix(assets, corr)

    # 4. Optimization
    max_sharpe_w = optimize_max_sharpe(assets, corr)
    min_var_w = optimize_min_variance(assets, corr)

    returns_arr = np.array([a.expected_return for a in assets])
    max_sharpe_metrics = portfolio_metrics(max_sharpe_w, returns_arr, cov)
    min_var_metrics = portfolio_metrics(min_var_w, returns_arr, cov)

    # 5. Efficient Frontier
    frontier = generate_efficient_frontier(assets, corr)

    return {
        "assets": assets,
        "excluded_assets": excluded_assets,
        "corr_matrix": corr,
        "cov_matrix": cov,
        "max_sharpe_weights": max_sharpe_w,
        "min_var_weights": min_var_w,
        "max_sharpe_metrics": max_sharpe_metrics,
        "min_var_metrics": min_var_metrics,
        "frontier": frontier,
        "included_indices": included_indices,
        "excluded_indices": excluded_indices,
        "data_sources": data_sources,
    }
