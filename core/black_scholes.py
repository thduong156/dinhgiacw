import numpy as np
from scipy.stats import norm


class BlackScholesModel:
    """
    Mô hình Black-Scholes cho quyền chọn kiểu Châu Âu.
    Hỗ trợ dividend yield (q) cho cổ phiếu trả cổ tức.

    Parameters:
        S: Giá cổ phiếu cơ sở hiện tại
        K: Giá thực hiện (strike price)
        T: Thời gian đến đáo hạn (năm)
        r: Lãi suất phi rủi ro (dạng thập phân, vd: 0.03 = 3%)
        sigma: Biến động giá (dạng thập phân, vd: 0.35 = 35%)
        option_type: "call" hoặc "put"
        q: Tỷ suất cổ tức liên tục (dạng thập phân, vd: 0.05 = 5%)
    """

    def __init__(self, S: float, K: float, T: float, r: float,
                 sigma: float, option_type: str = "call", q: float = 0.0):
        self.S = max(S, 0.0)
        self.K = max(K, 1e-6)  # K must be positive for log(S/K)
        self.T = max(T, 0.0)
        self.r = r
        self.sigma = max(sigma, 0.0)
        self.option_type = option_type.lower()
        self.q = q

    def d1(self) -> float:
        """d1 = [ln(S/K) + (r - q + sigma^2/2)*T] / (sigma*sqrt(T))"""
        if self.T <= 0 or self.sigma <= 0 or self.S <= 0:
            return 0.0
        return (np.log(self.S / self.K) + (self.r - self.q + 0.5 * self.sigma ** 2) * self.T) / (
            self.sigma * np.sqrt(self.T)
        )

    def d2(self) -> float:
        """d2 = d1 - sigma*sqrt(T)"""
        if self.T <= 0 or self.sigma <= 0 or self.S <= 0:
            return 0.0
        return self.d1() - self.sigma * np.sqrt(self.T)

    def price(self) -> float:
        """
        Tính giá quyền chọn theo Black-Scholes với dividend yield.
        Call: C = S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2)
        Put:  P = K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1)
        """
        if self.T <= 0 or self.S <= 0:
            return self._intrinsic_value()

        if self.sigma <= 0:
            raise ValueError("Biến động giá (sigma) phải lớn hơn 0")

        _d1 = self.d1()
        _d2 = self.d2()
        discount_r = np.exp(-self.r * self.T)
        discount_q = np.exp(-self.q * self.T)

        if self.option_type == "call":
            return self.S * discount_q * norm.cdf(_d1) - self.K * discount_r * norm.cdf(_d2)
        else:
            return self.K * discount_r * norm.cdf(-_d2) - self.S * discount_q * norm.cdf(-_d1)

    def _intrinsic_value(self) -> float:
        """Giá trị nội tại khi đã đáo hạn."""
        if self.option_type == "call":
            return max(0.0, self.S - self.K)
        else:
            return max(0.0, self.K - self.S)

    def warrant_price(self, conversion_ratio: float) -> float:
        """Giá chứng quyền = Giá quyền chọn / Tỷ lệ chuyển đổi."""
        return self.price() / conversion_ratio
