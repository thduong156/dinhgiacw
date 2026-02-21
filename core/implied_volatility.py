import numpy as np
from scipy.stats import norm
from core.black_scholes import BlackScholesModel


def solve_implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    conversion_ratio: float = 1.0,
    option_type: str = "call",
    max_iterations: int = 100,
    tolerance: float = 1e-8,
    sigma_init: float = 0.3,
    q: float = 0.0,
) -> float:
    """
    Tính biến động ngầm định (Implied Volatility) bằng Newton-Raphson
    với bisection fallback. Hỗ trợ dividend yield (q).

    Args:
        market_price: Giá CW thị trường
        S: Giá cổ phiếu cơ sở
        K: Giá thực hiện
        T: Thời gian đáo hạn (năm)
        r: Lãi suất phi rủi ro
        conversion_ratio: Tỷ lệ chuyển đổi
        option_type: "call" hoặc "put"
        q: Tỷ suất cổ tức liên tục

    Returns:
        Implied volatility (dạng thập phân)

    Raises:
        ValueError: Nếu không thể tìm được IV hợp lệ
    """
    if market_price <= 0:
        raise ValueError("Giá CW thị trường phải lớn hơn 0")
    if T <= 0:
        raise ValueError("Thời gian đáo hạn phải lớn hơn 0")

    # Chuyển giá CW sang giá option tương đương
    target_option_price = market_price * conversion_ratio

    # Kiểm tra giá có nằm trong khoảng hợp lệ (dùng discounted lower bound)
    discount_r = np.exp(-r * T)
    discount_q = np.exp(-q * T)
    if option_type == "call":
        lower_bound = max(0, S * discount_q - K * discount_r)
    else:
        lower_bound = max(0, K * discount_r - S * discount_q)
    if target_option_price < lower_bound * 0.95:
        raise ValueError("Giá CW thấp hơn giá trị nội tại - không hợp lệ")

    # Newton-Raphson
    sigma = sigma_init
    for i in range(max_iterations):
        model = BlackScholesModel(S, K, T, r, sigma, option_type, q=q)
        price = model.price()
        diff = price - target_option_price

        if abs(diff) < tolerance:
            return sigma

        # Vega (raw, không chia 100) — với dividend yield
        _d1 = model.d1()
        discount_q = np.exp(-q * T)
        vega = S * discount_q * norm.pdf(_d1) * np.sqrt(T)

        if abs(vega) < 1e-12:
            break  # Vega quá nhỏ, chuyển sang bisection

        sigma_new = sigma - diff / vega

        if sigma_new <= 0 or sigma_new > 10.0:
            break  # Ngoài khoảng hợp lệ, chuyển sang bisection

        sigma = sigma_new

    # Bisection fallback
    return _bisection_iv(target_option_price, S, K, T, r, option_type, q=q)


def _bisection_iv(
    target_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str,
    low: float = 0.001,
    high: float = 5.0,
    max_iter: int = 200,
    tol: float = 1e-8,
    q: float = 0.0,
) -> float:
    """Bisection method fallback cho IV solver."""
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        model = BlackScholesModel(S, K, T, r, mid, option_type, q=q)
        price = model.price()

        if abs(price - target_price) < tol:
            return mid

        if price > target_price:
            high = mid
        else:
            low = mid

    return (low + high) / 2.0
