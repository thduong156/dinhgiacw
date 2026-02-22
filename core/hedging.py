"""
Hedging Engine — Tính toán phòng hộ danh mục CP + CW.

Chiến lược:
  A. Protective Put:  Long stock + Long put CW
  B. Delta Hedging:   Điều chỉnh CP để đạt target Net Delta
  C. Combined:        Tối ưu Markowitz cho danh mục kết hợp
"""

from dataclasses import dataclass, field
import numpy as np

from core.black_scholes import BlackScholesModel
from core.greeks import GreeksCalculator
from core.warrant import WarrantAnalyzer


# ── Risk Profiles ────────────────────────────────────────────────

RISK_PROFILES = {
    "very_conservative": {
        "name_vi": "Rất Bảo Thủ",
        "icon": "I",
        "description": "Bảo toàn vốn tối đa, chỉ dùng put CW làm bảo hiểm",
        "target_stock_pct": (0.90, 0.95),
        "target_cw_pct": (0.05, 0.10),
        "target_net_delta": (0.0, 0.2),
        "max_leverage": 2.0,
        "preferred_strategy": "protective_put",
        "min_days_remaining": 120,
        "prefer_moneyness": ["ITM"],
        "color": "#22C55E",
    },
    "conservative": {
        "name_vi": "Bảo Thủ",
        "icon": "II",
        "description": "Ổn định, ưu tiên bảo vệ vốn với một ít upside",
        "target_stock_pct": (0.80, 0.90),
        "target_cw_pct": (0.10, 0.20),
        "target_net_delta": (0.2, 0.4),
        "max_leverage": 3.0,
        "preferred_strategy": "protective_put",
        "min_days_remaining": 90,
        "prefer_moneyness": ["ITM", "ATM"],
        "color": "#4ADE80",
    },
    "moderate": {
        "name_vi": "Cân Bằng",
        "icon": "III",
        "description": "Cân bằng lợi nhuận và rủi ro, delta hedging linh hoạt",
        "target_stock_pct": (0.60, 0.80),
        "target_cw_pct": (0.20, 0.40),
        "target_net_delta": (0.4, 0.6),
        "max_leverage": 5.0,
        "preferred_strategy": "delta_hedging",
        "min_days_remaining": 60,
        "prefer_moneyness": ["ITM", "ATM"],
        "color": "#F59E0B",
    },
    "growth": {
        "name_vi": "Tăng Trưởng",
        "icon": "IV",
        "description": "Ưu tiên sinh lời, chấp nhận biến động, dùng đòn bẩy CW",
        "target_stock_pct": (0.40, 0.60),
        "target_cw_pct": (0.40, 0.60),
        "target_net_delta": (0.6, 0.8),
        "max_leverage": 8.0,
        "preferred_strategy": "combined",
        "min_days_remaining": 30,
        "prefer_moneyness": ["ATM", "OTM"],
        "color": "#F97316",
    },
    "aggressive": {
        "name_vi": "Tích Cực",
        "icon": "V",
        "description": "Tối đa hoá lợi nhuận, đòn bẩy cao, chấp nhận rủi ro lớn",
        "target_stock_pct": (0.20, 0.40),
        "target_cw_pct": (0.60, 0.80),
        "target_net_delta": (0.8, 1.2),
        "max_leverage": 12.0,
        "preferred_strategy": "combined",
        "min_days_remaining": 15,
        "prefer_moneyness": ["ATM", "OTM"],
        "color": "#EF4444",
    },
}


# ── Data Models ──────────────────────────────────────────────────

@dataclass
class StockPosition:
    ticker: str
    entry_price: float
    quantity: int
    current_price: float


# ── Helper: tạo WarrantAnalyzer từ CW dict ──────────────────────

def _make_analyzer(cw: dict) -> WarrantAnalyzer:
    return WarrantAnalyzer(
        S=cw["S"], K=cw["K"], T=cw["T"], r=cw["r"],
        sigma=cw["sigma"], cw_market_price=cw["cw_price"],
        conversion_ratio=cw["cr"], option_type=cw.get("option_type", "call"),
        q=cw.get("q", 0.0),
    )


# ── 1. Net Greeks ────────────────────────────────────────────────

def calculate_net_greeks(stocks: list[StockPosition], cw_list: list[dict]) -> dict:
    """
    Tính Net Greeks tổng hợp cho danh mục CP + CW.

    Stock: delta = +1/share, gamma = theta = vega = 0.
    CW:    delta/gamma/theta/vega đã điều chỉnh CR (từ GreeksCalculator).

    Returns dict per-ticker breakdown + net totals.
    """
    per_ticker = {}

    # Stock contributions
    for sp in stocks:
        tk = sp.ticker.upper()
        if tk not in per_ticker:
            per_ticker[tk] = {
                "ticker": tk,
                "stock_delta": 0.0, "stock_value": 0.0,
                "cw_delta": 0.0, "cw_gamma": 0.0,
                "cw_theta": 0.0, "cw_vega": 0.0,
                "cw_value": 0.0,
            }
        per_ticker[tk]["stock_delta"] += sp.quantity  # 1 delta per share
        per_ticker[tk]["stock_value"] += sp.current_price * sp.quantity

    # CW contributions
    for cw in cw_list:
        tk = cw.get("ma_co_so", "").upper()
        qty = cw.get("quantity") or 0
        if qty == 0:
            continue
        if tk not in per_ticker:
            per_ticker[tk] = {
                "ticker": tk,
                "stock_delta": 0.0, "stock_value": 0.0,
                "cw_delta": 0.0, "cw_gamma": 0.0,
                "cw_theta": 0.0, "cw_vega": 0.0,
                "cw_value": 0.0,
            }
        analyzer = _make_analyzer(cw)
        greeks = analyzer.greeks.all_greeks()
        per_ticker[tk]["cw_delta"] += greeks["delta"] * qty
        per_ticker[tk]["cw_gamma"] += greeks["gamma"] * qty
        per_ticker[tk]["cw_theta"] += greeks["theta"] * qty
        per_ticker[tk]["cw_vega"] += greeks["vega"] * qty
        per_ticker[tk]["cw_value"] += cw["cw_price"] * qty

    # Aggregate
    net_delta = sum(v["stock_delta"] + v["cw_delta"] for v in per_ticker.values())
    net_gamma = sum(v["cw_gamma"] for v in per_ticker.values())
    net_theta = sum(v["cw_theta"] for v in per_ticker.values())
    net_vega = sum(v["cw_vega"] for v in per_ticker.values())

    total_stock_val = sum(v["stock_value"] for v in per_ticker.values())
    total_cw_val = sum(v["cw_value"] for v in per_ticker.values())
    total_val = total_stock_val + total_cw_val

    return {
        "net_delta": net_delta,
        "net_gamma": net_gamma,
        "net_theta": net_theta,
        "net_vega": net_vega,
        "per_ticker": list(per_ticker.values()),
        "total_stock_value": total_stock_val,
        "total_cw_value": total_cw_val,
        "total_value": total_val,
        "stock_pct": (total_stock_val / total_val * 100) if total_val > 0 else 0,
        "cw_pct": (total_cw_val / total_val * 100) if total_val > 0 else 0,
    }


# ── 2. Protective Put Analysis ──────────────────────────────────

def protective_put_analysis(stock_pos: StockPosition, put_cw_list: list[dict]) -> list[dict]:
    """
    Phân tích chiến lược Protective Put cho 1 cổ phiếu.

    Với mỗi put CW cùng underlying:
      - Tính chi phí bảo hiểm, break-even, max loss
      - Tạo payoff data
    """
    results = []
    for cw in put_cw_list:
        if cw.get("option_type", "call") != "put":
            continue
        if cw.get("ma_co_so", "").upper() != stock_pos.ticker.upper():
            continue

        cr = cw["cr"]
        put_price = cw["cw_price"]
        K = cw["K"]

        # Số CW cần mua để hedge toàn bộ vị thế CP
        put_qty_needed = int(np.ceil(stock_pos.quantity * cr))

        # Chi phí bảo hiểm
        cost_total = put_price * put_qty_needed
        stock_value = stock_pos.current_price * stock_pos.quantity
        cost_pct = (cost_total / stock_value * 100) if stock_value > 0 else 0

        # Break-even: giá CP cần tăng đủ bù chi phí put
        cost_per_share = cost_total / stock_pos.quantity if stock_pos.quantity > 0 else 0
        break_even = stock_pos.entry_price + cost_per_share

        # Max loss: giá CP giảm xuống K, put bù lại
        # Stock loss khi S→K: (entry - K) per share (nếu entry > K)
        # Plus put cost
        max_loss_per_share = max(0, stock_pos.entry_price - K) + cost_per_share
        max_loss = max_loss_per_share * stock_pos.quantity
        max_loss_pct = (max_loss / stock_value * 100) if stock_value > 0 else 0

        # Payoff data: PnL vs stock price at expiry
        s_range = np.linspace(
            stock_pos.current_price * 0.5,
            stock_pos.current_price * 1.5,
            100,
        )
        stock_pnl = (s_range - stock_pos.entry_price) * stock_pos.quantity
        # Put CW payoff at expiry: max(0, K - S) / CR * qty - cost
        put_payoff = np.maximum(0, K - s_range) / cr * put_qty_needed - cost_total
        total_pnl = stock_pnl + put_payoff

        analyzer = _make_analyzer(cw)
        analysis = analyzer.full_analysis()

        results.append({
            "ma_cw": cw.get("ma_cw", ""),
            "K": K,
            "cr": cr,
            "put_price": put_price,
            "put_qty_needed": put_qty_needed,
            "cost_total": cost_total,
            "cost_pct": cost_pct,
            "break_even": break_even,
            "max_loss": max_loss,
            "max_loss_pct": max_loss_pct,
            "protection_level": K,
            "days_remaining": cw.get("days_remaining", 0),
            "moneyness": analysis["moneyness"],
            "payoff_data": {
                "prices": s_range.tolist(),
                "stock_pnl": stock_pnl.tolist(),
                "put_pnl": put_payoff.tolist(),
                "total_pnl": total_pnl.tolist(),
            },
        })

    # Sort by cost_pct ascending (cheapest protection first)
    results.sort(key=lambda x: x["cost_pct"])
    return results


# ── 3. Delta Hedge Recommendation ───────────────────────────────

def delta_hedge_recommendation(
    stocks: list[StockPosition],
    cw_list: list[dict],
    target_delta: float = 0.0,
) -> dict:
    """
    Đề xuất điều chỉnh để đạt Net Delta mục tiêu.
    """
    greeks = calculate_net_greeks(stocks, cw_list)
    current = greeks["net_delta"]
    gap = target_delta - current

    recommendations = []
    shares_adj = 0
    cost = 0.0

    if abs(gap) < 1:
        recommendations.append("Danh mục đã gần đạt target delta. Không cần điều chỉnh.")
    elif gap > 0:
        # Cần thêm delta → mua CP
        shares_adj = int(np.ceil(gap))
        # Ước tính giá mua bằng giá CP đầu tiên có trong stocks hoặc CW
        avg_price = 0
        for sp in stocks:
            avg_price = sp.current_price
            break
        if avg_price == 0:
            for cw in cw_list:
                avg_price = cw.get("S", 0)
                if avg_price > 0:
                    break
        cost = shares_adj * avg_price
        recommendations.append(
            f"Mua thêm {shares_adj:,} cổ phiếu để tăng delta lên {target_delta:.1f}"
        )
        recommendations.append(f"Chi phí ước tính: {cost:,.0f} VND")
    else:
        # Cần giảm delta → bán CP hoặc mua put CW
        shares_to_sell = int(np.ceil(abs(gap)))
        total_stock_shares = sum(sp.quantity for sp in stocks)

        if shares_to_sell <= total_stock_shares:
            shares_adj = -shares_to_sell
            avg_price = stocks[0].current_price if stocks else 0
            cost = shares_to_sell * avg_price  # proceeds
            recommendations.append(
                f"Bán bớt {shares_to_sell:,} cổ phiếu để giảm delta xuống {target_delta:.1f}"
            )
        else:
            # Cần mua put CW để giảm delta
            puts_available = [cw for cw in cw_list if cw.get("option_type") == "put"]
            if puts_available:
                put = puts_available[0]
                analyzer = _make_analyzer(put)
                put_delta = analyzer.greeks.delta()  # negative for puts
                if abs(put_delta) > 1e-6:
                    put_qty = int(np.ceil(abs(gap) / abs(put_delta)))
                    cost = put_qty * put["cw_price"]
                    recommendations.append(
                        f"Mua {put_qty:,} put CW {put.get('ma_cw', '')} "
                        f"(delta = {put_delta:.4f}) để giảm delta"
                    )
                    recommendations.append(f"Chi phí: {cost:,.0f} VND")
            else:
                shares_adj = -shares_to_sell
                recommendations.append(
                    f"Bán bớt {shares_to_sell:,} cổ phiếu "
                    f"(không có put CW khả dụng)"
                )

    # Rebalance trigger: ±20% of target range
    trigger = max(abs(target_delta) * 0.2, 5.0)

    return {
        "current_delta": current,
        "target_delta": target_delta,
        "delta_gap": gap,
        "shares_adjustment": shares_adj,
        "adjustment_cost": cost,
        "new_net_delta": current + shares_adj,
        "rebalance_trigger": trigger,
        "recommendations": recommendations,
        "per_ticker": greeks["per_ticker"],
    }


# ── 4. Build Hedged Portfolio ────────────────────────────────────

def build_hedged_portfolio(
    stocks: list[StockPosition],
    cw_list: list[dict],
    profile_key: str,
    budget: float = 0,
) -> dict:
    """
    Xây dựng danh mục phòng hộ tối ưu theo khẩu vị rủi ro.
    """
    profile = RISK_PROFILES.get(profile_key, RISK_PROFILES["moderate"])
    greeks = calculate_net_greeks(stocks, cw_list)
    target_lo, target_hi = profile["target_net_delta"]
    target_mid = (target_lo + target_hi) / 2

    # Filter CW phù hợp risk profile
    filtered_cw = []
    excluded_cw = []
    for cw in cw_list:
        days = cw.get("days_remaining", 0)
        analyzer = _make_analyzer(cw)
        lev = analyzer.effective_leverage()
        moneyness = analyzer.moneyness()
        moneyness_short = moneyness.split(" ")[0]  # "ITM", "ATM", "OTM"

        ok = True
        reason = ""
        if days < profile["min_days_remaining"]:
            ok = False
            reason = f"Quá ngắn hạn ({days} ngày < {profile['min_days_remaining']})"
        elif lev > profile["max_leverage"]:
            ok = False
            reason = f"Đòn bẩy quá cao ({lev:.1f}x > {profile['max_leverage']}x)"
        elif moneyness_short not in profile["prefer_moneyness"]:
            ok = False
            reason = f"{moneyness_short} không phù hợp (cần {profile['prefer_moneyness']})"

        if ok:
            filtered_cw.append(cw)
        else:
            excluded_cw.append({"cw": cw, "reason": reason})

    # Delta hedge recommendation
    delta_rec = delta_hedge_recommendation(stocks, filtered_cw, target_mid)

    # Allocation summary
    stock_alloc = []
    for sp in stocks:
        val = sp.current_price * sp.quantity
        stock_alloc.append({
            "type": "CP",
            "ticker": sp.ticker.upper(),
            "price": sp.current_price,
            "quantity": sp.quantity,
            "value": val,
            "delta": sp.quantity,
        })

    cw_alloc = []
    for cw in filtered_cw:
        qty = cw.get("quantity") or 0
        val = cw["cw_price"] * qty
        analyzer = _make_analyzer(cw)
        d = analyzer.greeks.delta() * qty
        cw_alloc.append({
            "type": "CW",
            "ticker": cw.get("ma_cw", "").upper(),
            "underlying": cw.get("ma_co_so", "").upper(),
            "option_type": cw.get("option_type", "call"),
            "price": cw["cw_price"],
            "quantity": qty,
            "value": val,
            "delta": d,
            "days_remaining": cw.get("days_remaining", 0),
            "leverage": analyzer.effective_leverage(),
        })

    total_val = greeks["total_value"]

    # Assess current vs target
    current_stock_pct = greeks["stock_pct"]
    target_stock_lo, target_stock_hi = [x * 100 for x in profile["target_stock_pct"]]
    in_target_stock = target_stock_lo <= current_stock_pct <= target_stock_hi
    in_target_delta = target_lo <= greeks["net_delta"] <= target_hi

    # Recommendations
    recs = []
    if not in_target_stock:
        if current_stock_pct > target_stock_hi:
            recs.append(
                f"Tỷ trọng CP ({current_stock_pct:.0f}%) cao hơn mục tiêu "
                f"({target_stock_lo:.0f}-{target_stock_hi:.0f}%). "
                f"Cân nhắc tăng vị thế CW."
            )
        else:
            recs.append(
                f"Tỷ trọng CP ({current_stock_pct:.0f}%) thấp hơn mục tiêu "
                f"({target_stock_lo:.0f}-{target_stock_hi:.0f}%). "
                f"Cân nhắc tăng vị thế CP hoặc giảm CW."
            )

    if not in_target_delta:
        recs.extend(delta_rec["recommendations"])

    if excluded_cw:
        names = ", ".join(c["cw"]["ma_cw"] for c in excluded_cw)
        recs.append(f"CW bị loại khỏi danh mục phù hợp: {names}")

    return {
        "profile": profile,
        "profile_key": profile_key,
        "stock_allocation": stock_alloc,
        "cw_allocation": cw_alloc,
        "filtered_cw": filtered_cw,
        "excluded_cw": excluded_cw,
        "net_greeks": greeks,
        "delta_recommendation": delta_rec,
        "total_value": total_val,
        "in_target_stock": in_target_stock,
        "in_target_delta": in_target_delta,
        "recommendations": recs,
    }


# ── 5. Payoff Data ──────────────────────────────────────────────

def generate_payoff_data(
    stocks: list[StockPosition],
    cw_list: list[dict],
    n_points: int = 100,
) -> dict:
    """
    Tạo dữ liệu payoff diagram cho danh mục tổng hợp CP + CW.
    """
    # Tìm giá CP trung bình để xác định range
    prices = [sp.current_price for sp in stocks if sp.current_price > 0]
    for cw in cw_list:
        if cw.get("S", 0) > 0:
            prices.append(cw["S"])
    if not prices:
        return {"prices": [], "stock_pnl": [], "cw_pnl": [], "total_pnl": []}

    avg_price = np.mean(prices)
    s_range = np.linspace(avg_price * 0.5, avg_price * 1.5, n_points)

    stock_pnl = np.zeros(n_points)
    cw_pnl = np.zeros(n_points)

    # Stock PnL: (S_new - entry) × qty
    for sp in stocks:
        stock_pnl += (s_range - sp.entry_price) * sp.quantity

    # CW PnL at expiry: (max(0, payoff) / CR - entry) × qty
    for cw in cw_list:
        qty = cw.get("quantity") or 0
        if qty == 0:
            continue
        K = cw["K"]
        cr = cw["cr"]
        entry = cw.get("entry_price") or cw["cw_price"]
        opt_type = cw.get("option_type", "call")

        if opt_type == "call":
            intrinsic = np.maximum(0, s_range - K) / cr
        else:
            intrinsic = np.maximum(0, K - s_range) / cr

        cw_pnl += (intrinsic - entry) * qty

    total_pnl = stock_pnl + cw_pnl

    # Find break-even(s)
    break_evens = []
    for i in range(len(total_pnl) - 1):
        if total_pnl[i] * total_pnl[i + 1] < 0:
            # Linear interpolation
            ratio = abs(total_pnl[i]) / (abs(total_pnl[i]) + abs(total_pnl[i + 1]))
            be = s_range[i] + ratio * (s_range[i + 1] - s_range[i])
            break_evens.append(float(be))

    return {
        "prices": s_range.tolist(),
        "stock_pnl": stock_pnl.tolist(),
        "cw_pnl": cw_pnl.tolist(),
        "total_pnl": total_pnl.tolist(),
        "break_evens": break_evens,
    }
