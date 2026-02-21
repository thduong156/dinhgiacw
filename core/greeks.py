import numpy as np
from scipy.stats import norm
from core.black_scholes import BlackScholesModel


class GreeksCalculator:
    """
    Tính các chỉ số Greeks cho chứng quyền.
    Tất cả đều được điều chỉnh theo tỷ lệ chuyển đổi (CR).
    Hỗ trợ dividend yield (q) từ BlackScholesModel.
    """

    def __init__(self, model: BlackScholesModel, conversion_ratio: float = 1.0):
        self.model = model
        self.cr = conversion_ratio

    # ------ Helpers ------
    def _discount_q(self) -> float:
        """e^(-qT) — dividend discount factor."""
        return np.exp(-self.model.q * self.model.T)

    # ------ First-order Greeks ------
    def delta(self) -> float:
        """
        Delta: Độ nhạy giá CW theo giá cổ phiếu cơ sở.
        Call Delta = e^(-qT) * N(d1) / CR
        Put Delta  = e^(-qT) * (N(d1) - 1) / CR
        """
        if self.model.T <= 0:
            if self.model.option_type == "call":
                return (1.0 if self.model.S > self.model.K else 0.0) / self.cr
            else:
                return (-1.0 if self.model.S < self.model.K else 0.0) / self.cr

        _d1 = self.model.d1()
        dq = self._discount_q()
        if self.model.option_type == "call":
            return dq * norm.cdf(_d1) / self.cr
        else:
            return dq * (norm.cdf(_d1) - 1.0) / self.cr

    def delta_raw(self) -> float:
        """Delta chưa điều chỉnh CR (dùng cho effective leverage)."""
        if self.model.T <= 0:
            if self.model.option_type == "call":
                return 1.0 if self.model.S > self.model.K else 0.0
            else:
                return -1.0 if self.model.S < self.model.K else 0.0

        _d1 = self.model.d1()
        dq = self._discount_q()
        if self.model.option_type == "call":
            return dq * norm.cdf(_d1)
        else:
            return dq * (norm.cdf(_d1) - 1.0)

    def gamma(self) -> float:
        """
        Gamma: Tốc độ thay đổi Delta.
        Gamma = e^(-qT) * N'(d1) / (S * sigma * sqrt(T)) / CR
        """
        if self.model.T <= 0 or self.model.sigma <= 0 or self.model.S <= 0:
            return 0.0

        _d1 = self.model.d1()
        S = self.model.S
        sigma = self.model.sigma
        T = self.model.T
        dq = self._discount_q()
        return dq * norm.pdf(_d1) / (S * sigma * np.sqrt(T)) / self.cr

    def vega(self) -> float:
        """
        Vega: Độ nhạy theo biến động giá (per 1% thay đổi sigma).
        Vega = S * e^(-qT) * N'(d1) * sqrt(T) / 100 / CR
        """
        if self.model.T <= 0 or self.model.sigma <= 0:
            return 0.0

        _d1 = self.model.d1()
        dq = self._discount_q()
        return self.model.S * dq * norm.pdf(_d1) * np.sqrt(self.model.T) / 100.0 / self.cr

    def theta(self) -> float:
        """
        Theta: Suy giảm giá trị theo thời gian (per ngày).
        Với dividend yield q:
        Call: -[S*e^(-qT)*N'(d1)*sigma/(2*sqrt(T))] + q*S*e^(-qT)*N(d1) - r*K*e^(-rT)*N(d2)
        Put:  -[S*e^(-qT)*N'(d1)*sigma/(2*sqrt(T))] - q*S*e^(-qT)*N(-d1) + r*K*e^(-rT)*N(-d2)
        Chia cho 365 (daily) và CR.
        """
        if self.model.T <= 0:
            return 0.0

        _d1 = self.model.d1()
        _d2 = self.model.d2()
        S = self.model.S
        K = self.model.K
        r = self.model.r
        q = self.model.q
        T = self.model.T
        sigma = self.model.sigma
        discount_r = np.exp(-r * T)
        discount_q = np.exp(-q * T)

        # Term 1: time decay (luôn âm)
        term1 = -(S * discount_q * norm.pdf(_d1) * sigma) / (2.0 * np.sqrt(T))

        if self.model.option_type == "call":
            term2 = -r * K * discount_r * norm.cdf(_d2)
            term3 = q * S * discount_q * norm.cdf(_d1)
        else:
            term2 = r * K * discount_r * norm.cdf(-_d2)
            term3 = -q * S * discount_q * norm.cdf(-_d1)

        return (term1 + term2 + term3) / 365.0 / self.cr

    def rho(self) -> float:
        """
        Rho: Độ nhạy theo lãi suất (per 1% thay đổi r).
        Call: K*T*e^(-rT)*N(d2) / 100
        Put: -K*T*e^(-rT)*N(-d2) / 100
        Chia cho CR.
        """
        if self.model.T <= 0:
            return 0.0

        _d2 = self.model.d2()
        K = self.model.K
        T = self.model.T
        r = self.model.r
        discount = np.exp(-r * T)

        if self.model.option_type == "call":
            return K * T * discount * norm.cdf(_d2) / 100.0 / self.cr
        else:
            return -K * T * discount * norm.cdf(-_d2) / 100.0 / self.cr

    def all_greeks(self) -> dict:
        """Trả về tất cả Greeks trong một dict."""
        return {
            "delta": self.delta(),
            "gamma": self.gamma(),
            "vega": self.vega(),
            "theta": self.theta(),
            "rho": self.rho(),
        }
