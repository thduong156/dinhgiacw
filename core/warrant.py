import numpy as np
from scipy.stats import norm
from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from core.implied_volatility import solve_implied_volatility


class WarrantAnalyzer:
    """
    Phân tích chứng quyền Việt Nam.
    Kết hợp Black-Scholes pricing, Greeks, và các chỉ số đặc thù CW.
    Hỗ trợ dividend yield (q) cho cổ phiếu trả cổ tức.
    """

    def __init__(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        cw_market_price: float,
        conversion_ratio: float,
        option_type: str = "call",
        q: float = 0.0,
    ):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.cw_market_price = cw_market_price
        self.cr = conversion_ratio
        self.option_type = option_type.lower()
        self.q = q

        self.model = BlackScholesModel(S, K, T, r, sigma, option_type, q=q)
        self.greeks = GreeksCalculator(self.model, conversion_ratio)

    def theoretical_cw_price(self) -> float:
        """Giá CW lý thuyết = Giá option / Tỷ lệ chuyển đổi."""
        return self.model.price() / self.cr

    def intrinsic_value(self) -> float:
        """Giá trị nội tại của CW."""
        if self.option_type == "call":
            return max(0.0, (self.S - self.K)) / self.cr
        else:
            return max(0.0, (self.K - self.S)) / self.cr

    def time_value(self) -> float:
        """Giá trị thời gian = Giá lý thuyết - Giá trị nội tại."""
        return max(0.0, self.theoretical_cw_price() - self.intrinsic_value())

    def break_even(self) -> float:
        """
        Điểm hòa vốn.
        Call: Strike + CW_price * CR
        Put:  Strike - CW_price * CR (clamped to >= 0)
        """
        if self.option_type == "call":
            return self.K + self.cw_market_price * self.cr
        else:
            return max(0.0, self.K - self.cw_market_price * self.cr)

    def break_even_change_pct(self) -> float:
        """% thay đổi giá cơ sở cần để hòa vốn."""
        be = self.break_even()
        if self.S <= 0:
            return 0.0
        return ((be - self.S) / self.S) * 100.0

    def gearing(self) -> float:
        """Tỷ lệ đòn bẩy đơn giản = S / (CW_price * CR)."""
        denominator = self.cw_market_price * self.cr
        if denominator <= 0:
            return 0.0
        return self.S / denominator

    def effective_leverage(self) -> float:
        """Đòn bẩy hiệu dụng = |Delta_raw| * Gearing."""
        raw_delta = abs(self.greeks.delta_raw())
        return raw_delta * self.gearing()

    def premium_discount(self) -> dict:
        """
        So sánh giá lý thuyết vs giá thị trường.
        Premium (+) = CW đang đắt hơn giá trị thực.
        Discount (-) = CW đang rẻ hơn giá trị thực.
        """
        theo = self.theoretical_cw_price()
        diff = self.cw_market_price - theo
        pct = (diff / theo) * 100.0 if theo > 0 else 0.0

        if diff > 0.01:
            status = "Premium"
            status_vi = "Đang đắt (Premium)"
        elif diff < -0.01:
            status = "Discount"
            status_vi = "Đang rẻ (Discount)"
        else:
            status = "Fair"
            status_vi = "Hợp lý (Fair Value)"

        return {
            "theoretical_price": theo,
            "market_price": self.cw_market_price,
            "difference": diff,
            "percentage": pct,
            "status": status,
            "status_vi": status_vi,
        }

    def moneyness(self) -> str:
        """Trạng thái moneyness: ITM, ATM, OTM."""
        if self.option_type == "call":
            if self.S > self.K * 1.02:
                return "ITM (Trong tiền)"
            elif self.S < self.K * 0.98:
                return "OTM (Ngoài tiền)"
            else:
                return "ATM (Ngang giá)"
        else:
            if self.S < self.K * 0.98:
                return "ITM (Trong tiền)"
            elif self.S > self.K * 1.02:
                return "OTM (Ngoài tiền)"
            else:
                return "ATM (Ngang giá)"

    def implied_volatility(self) -> float:
        """Tính IV từ giá thị trường."""
        return solve_implied_volatility(
            self.cw_market_price, self.S, self.K, self.T,
            self.r, self.cr, self.option_type, q=self.q
        )

    def probability_of_profit(self) -> float:
        """
        Xác suất CW có lãi tại đáo hạn (risk-neutral).
        Call: N(d2) — xác suất S > K tại expiry.
        Put:  N(-d2) — xác suất S < K tại expiry.
        Lưu ý: Đây là xác suất dựa trên break-even, không phải strike.
        """
        if self.T <= 0:
            return 0.0
        # Break-even based: tính d2 với break-even thay vì K
        be = self.break_even()
        if be <= 0:
            return 0.0
        sigma = self.sigma
        T = self.T
        r = self.r
        q = self.q
        if sigma <= 0 or T <= 0:
            return 0.0
        d2_be = (np.log(self.S / be) + (r - q - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        if self.option_type == "call":
            return float(norm.cdf(d2_be))
        else:
            return float(norm.cdf(-d2_be))

    def probability_itm(self) -> float:
        """Xác suất CW kết thúc ITM tại đáo hạn = N(d2) cho call."""
        if self.T <= 0 or self.sigma <= 0:
            return 0.0
        _d2 = self.model.d2()
        if self.option_type == "call":
            return float(norm.cdf(_d2))
        else:
            return float(norm.cdf(-_d2))

    def theta_efficiency(self) -> float:
        """
        Theta Efficiency: Bao nhiêu ngày theta cover được time value?
        = time_value / |theta_per_day|
        Càng cao càng tốt (CW "rẻ" về time decay).
        """
        if self.T <= 0:
            return 0.0  # Expired warrant — theta efficiency = 0
        tv = self.time_value()
        theta = abs(self.greeks.theta())
        if theta < 1e-6:
            return 999.0  # Theta gần 0 = rất tốt
        return min(tv / theta, 999.0)  # Cap to prevent display overflow

    @staticmethod
    def price_tick_round(price: float, tick: float = 10.0) -> float:
        """Làm tròn giá CW theo bước giá (10 VND mặc định trên HOSE)."""
        if tick <= 0:
            return price
        return round(price / tick) * tick

    def scenario_prices(self, price_changes_pct: list, vol_changes_pct: list) -> dict:
        """
        Bảng kịch bản giá CW theo thay đổi giá cơ sở và biến động.
        Returns dict với key = (price_change, vol_change), value = cw_price.
        """
        results = {}
        for dp in price_changes_pct:
            for dv in vol_changes_pct:
                new_S = self.S * (1 + dp / 100.0)
                new_sigma = self.sigma + dv / 100.0
                if new_sigma <= 0:
                    new_sigma = 0.01
                model = BlackScholesModel(new_S, self.K, self.T, self.r, new_sigma, self.option_type, q=self.q)
                results[(dp, dv)] = model.price() / self.cr
        return results

    def time_decay_prices(self, days_list: list) -> list:
        """Giá CW theo số ngày còn lại."""
        results = []
        for days in days_list:
            T_new = max(days / 365.0, 0.001)
            model = BlackScholesModel(self.S, self.K, T_new, self.r, self.sigma, self.option_type, q=self.q)
            results.append({"days": days, "price": model.price() / self.cr})
        return results

    def full_analysis(self) -> dict:
        """Phân tích toàn diện."""
        greeks = self.greeks.all_greeks()
        pd_info = self.premium_discount()

        try:
            iv = self.implied_volatility()
        except (ValueError, Exception):
            iv = None

        return {
            "theoretical_price": self.theoretical_cw_price(),
            "theoretical_price_tick": self.price_tick_round(self.theoretical_cw_price()),
            "intrinsic_value": self.intrinsic_value(),
            "time_value": self.time_value(),
            "break_even": self.break_even(),
            "break_even_change_pct": self.break_even_change_pct(),
            "moneyness": self.moneyness(),
            "gearing": self.gearing(),
            "effective_leverage": self.effective_leverage(),
            "implied_volatility": iv,
            "probability_itm": self.probability_itm(),
            "probability_of_profit": self.probability_of_profit(),
            "theta_efficiency": self.theta_efficiency(),
            "greeks": greeks,
            "premium_discount": pd_info,
        }
