from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.returns.calculator import ReturnsCalculator
from backend.src.calculations_v2.risk.calculator import RiskCalculator
from backend.src.calculations_v2.performance.calculator import PerformanceCalculator
from backend.src.calculations_v2.technical.indicators import TechnicalIndicators
from backend.src.calculations_v2.factors.momentum import MomentumFactors
from backend.src.calculations_v2.factors.value import ValueFactors
from backend.src.calculations_v2.factors.growth import GrowthFactors
from backend.src.calculations_v2.factors.quality import QualityFactors
from backend.src.calculations_v2.factors.volatility import VolatilityFactors


def main() -> None:
    ticker = "NVDA"
    end = datetime.now()
    start = end - timedelta(days=365 * 4)

    ds = DataService()

    # OHLCV for technicals and close series for returns
    price_frame = ds.get_price_data(ticker, start, end).frame
    close = price_frame["close"].astype(float)

    try:
        dividends = ds.get_dividends(ticker, start, end).series
    except Exception:
        dividends = pd.Series(dtype=float)

    # -------------------- Returns (single asset) -------------------- #
    r_price = ReturnsCalculator.daily_price_returns(close)
    r_total = ReturnsCalculator.total_returns(close, dividends if not dividends.empty else None)
    ann_price = ReturnsCalculator.annualized_return(r_price)
    ann_total = ReturnsCalculator.annualized_return(r_total)
    hpr_cash = ReturnsCalculator.holding_period_return_price_plus_divs_cash(
        close, dividends if not dividends.empty else None
    )
    hpr_reinv = ReturnsCalculator.holding_period_return_total_reinvested(
        close, dividends if not dividends.empty else None
    )

    # ------------------------ Risk (single) ------------------------ #
    vol_ann = RiskCalculator.annualized_volatility(r_price)
    mdd = RiskCalculator.max_drawdown(close)
    pvar = RiskCalculator.parametric_var(annual_vol=vol_ann)
    hvar = RiskCalculator.historical_var(r_price)
    es = RiskCalculator.expected_shortfall(r_price)
    ui_price = RiskCalculator.ulcer_index(close)

    returns_df = r_price.to_frame(ticker)
    mc_var = RiskCalculator.monte_carlo_var(weights=pd.Series({ticker: 1.0}), returns_df=returns_df, random_state=42)

    cov = returns_df.cov()
    mv, cv = RiskCalculator.marginal_var(
        weights=pd.Series({ticker: 1.0}), cov_daily=cov, as_percent_of_portfolio_var=True
    )
    dr = (
        RiskCalculator.diversification_ratio(weights=pd.Series({ticker: 1.0}), cov=cov)
        if not cov.empty
        else np.nan
    )

    # ---------------------- Performance (single) ---------------------- #
    sharpe = PerformanceCalculator.sharpe_ratio(r_price)
    sortino = PerformanceCalculator.sortino_ratio(r_price)
    calmar = PerformanceCalculator.calmar_from_returns(r_price)
    omega = PerformanceCalculator.omega_ratio(r_price)
    omega_ann = PerformanceCalculator.omega_ratio_from_annual(r_price, mar_annual=0.0)
    burke = PerformanceCalculator.burke_ratio(r_price)
    martin = PerformanceCalculator.martin_ratio(r_price)
    win_rate = PerformanceCalculator.win_rate(r_price)
    profit_factor = PerformanceCalculator.profit_factor_from_returns(r_price)
    profit_factor_eq = PerformanceCalculator.profit_factor(r_price, start_equity=1.0)
    tail = PerformanceCalculator.tail_ratio(r_price)
    gain_loss = PerformanceCalculator.gain_loss_ratio(r_price)
    ui_perf = PerformanceCalculator.ulcer_index(r_price)
    ui_prices = PerformanceCalculator.ulcer_index_from_prices(close)
    ui_monthly = PerformanceCalculator.ulcer_index_monthly(r_price)
    cagr = PerformanceCalculator.cagr_from_returns(r_price)
    # direct sterling using cagr and drawdown over same window
    eq_curve = (1.0 + r_price).cumprod()
    dd_series = PerformanceCalculator.drawdown_series(eq_curve)
    mdd_from_r = float(dd_series.min()) if not dd_series.empty else np.nan
    sterling_direct = PerformanceCalculator.sterling_ratio(cagr, mdd_from_r)
    # kappa ratio
    kappa = PerformanceCalculator.kappa_ratio(r_price)

    # Market/benchmark dependent metrics
    # Fetch SPY for market/benchmark
    try:
        spy = ds.get_bulk_close_series(["SPY"], start, end).get("SPY")
        rm = pd.Series(spy).astype(float).pct_change(fill_method=None).dropna() if spy is not None else pd.Series(dtype=float)
    except Exception:
        rm = pd.Series(dtype=float)
    treynor = PerformanceCalculator.treynor_ratio(r_price, rm) if not rm.empty else np.nan
    info = PerformanceCalculator.information_ratio(r_price, rm) if not rm.empty else np.nan
    alpha = PerformanceCalculator.alpha_jensen(r_price, rm) if not rm.empty else np.nan
    tracking_err = PerformanceCalculator.tracking_error(r_price, rm) if not rm.empty else np.nan
    appraisal = PerformanceCalculator.appraisal_ratio(r_price, rm) if not rm.empty else np.nan
    up_cap_d, down_cap_d = PerformanceCalculator.capture_ratios(r_price, rm, periods_per_year=None) if not rm.empty else (np.nan, np.nan)
    up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(r_price, rm, periods_per_year=252) if not rm.empty else (np.nan, np.nan)

    # ---------------------- Technical Indicators ---------------------- #
    ti = TechnicalIndicators(price_frame)
    ema = ti.ema(20).iloc[-1]
    wma = ti.wma(20).iloc[-1]
    vwap = ti.vwap(20).iloc[-1]
    bb_l, bb_m, bb_u = ti.bollinger_bands(20, 2.0)
    stoch_k, stoch_d = ti.stochastic(14, 3)
    atr_sma = ti.atr(14).iloc[-1]
    atr_w = ti.atr_wilder(14).iloc[-1]
    don_l, don_u = ti.donchian(20)
    kel_l, kel_m, kel_u = ti.keltner()
    psar = ti.parabolic_sar().iloc[-1]
    adx = ti.adx(14).iloc[-1]
    cci = ti.cci(20).iloc[-1]

    # ----------------------------- Output ----------------------------- #
    print(f"Ticker: {ticker}")
    print("\nReturns:")
    print({
        "ann_price": ann_price,
        "ann_total": ann_total,
        "hpr_cash": hpr_cash,
        "hpr_reinv": hpr_reinv,
        "ann_price_wrapper": ReturnsCalculator.annualized_price_return(close),
        "ann_total_wrapper": ReturnsCalculator.annualized_total_return(close, dividends if not dividends.empty else None),
    })

    print("\nRisk:")
    print({
        "vol_ann": vol_ann,
        "max_dd": mdd,
        "param_var": pvar,
        "hist_var": hvar,
        "es": es,
        "ulcer_price": ui_price,
        "mc_var": mc_var,
        "marginal_var": float(mv.iloc[0]) if not mv.empty else np.nan,
        "component_var_pct": float(cv.iloc[0]) if not cv.empty else np.nan,
        "diversification_ratio": dr,
        "parametric_cvar": RiskCalculator.parametric_cvar(vol_ann) if np.isfinite(vol_ann) else np.nan,
        "beta": RiskCalculator.beta(r_price, rm) if not rm.empty else np.nan,
        "up_beta": RiskCalculator.up_down_beta(r_price, rm)[0] if not rm.empty else np.nan,
        "down_beta": RiskCalculator.up_down_beta(r_price, rm)[1] if not rm.empty else np.nan,
        "corr_matrix_1x1": RiskCalculator.correlation_matrix(returns_df),
        "cov_matrix_1x1": RiskCalculator.covariance_matrix(returns_df),
        "pos_size_from_var_budget": RiskCalculator.position_size_from_var_budget(1000.0, vol_ann) if np.isfinite(vol_ann) else np.nan,
    })

    print("\nPerformance:")
    print({
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "omega": omega,
        "omega_from_annual": omega_ann,
        "burke": burke,
        "martin": martin,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "profit_factor_eq": profit_factor_eq,
        "profit_factor_from_pnl": PerformanceCalculator.profit_factor_from_pnl(((1.0 + r_price).cumprod().shift(1) * r_price).dropna()),
        "tail_ratio": tail,
        "gain_loss": gain_loss,
        "ulcer_index": ui_perf,
        "ulcer_from_prices": ui_prices,
        "ulcer_monthly": ui_monthly,
        "cagr": cagr,
        "sterling_direct": sterling_direct,
        "kappa": kappa,
        "treynor": treynor,
        "information": info,
        "alpha_jensen": alpha,
        "tracking_error": tracking_err,
        "appraisal_ratio": appraisal,
        "up_cap_daily": up_cap_d,
        "down_cap_daily": down_cap_d,
        "up_cap_ann": up_cap_ann,
        "down_cap_ann": down_cap_ann,
    })

    print("\nTechnicals (latest point values where applicable):")
    print({
        "ema20": float(ema) if np.isfinite(ema) else np.nan,
        "wma20": float(wma) if np.isfinite(wma) else np.nan,
        "vwap20": float(vwap) if np.isfinite(vwap) else np.nan,
        "bb_lower": float(bb_l.iloc[-1]) if not bb_l.empty else np.nan,
        "bb_mid": float(bb_m.iloc[-1]) if not bb_m.empty else np.nan,
        "bb_upper": float(bb_u.iloc[-1]) if not bb_u.empty else np.nan,
        "%K": float(stoch_k.iloc[-1]) if not stoch_k.empty else np.nan,
        "%D": float(stoch_d.iloc[-1]) if not stoch_d.empty else np.nan,
        "atr14_sma": float(atr_sma) if np.isfinite(atr_sma) else np.nan,
        "atr14_wilder": float(atr_w) if np.isfinite(atr_w) else np.nan,
        "donchian_low": float(don_l.iloc[-1]) if not don_l.empty else np.nan,
        "donchian_high": float(don_u.iloc[-1]) if not don_u.empty else np.nan,
        "keltner_low": float(kel_l.iloc[-1]) if not kel_l.empty else np.nan,
        "keltner_mid": float(kel_m.iloc[-1]) if not kel_m.empty else np.nan,
        "keltner_high": float(kel_u.iloc[-1]) if not kel_u.empty else np.nan,
        "psar": float(psar) if np.isfinite(psar) else np.nan,
        "adx14": float(adx) if np.isfinite(adx) else np.nan,
        "cci20": float(cci) if np.isfinite(cci) else np.nan,
    })

    # ------------------------------ Factors ------------------------------ #
    print("\nFactors:")
    # Momentum (price-based)
    try:
        # Market series for idio momentum
        spy = ds.get_bulk_close_series(["SPY"], start, end).get("SPY")
        mkt_px = pd.Series(spy).astype(float).reindex(close.index) if spy is not None else None
    except Exception:
        mkt_px = None
    mf = MomentumFactors(price_series=close, dividends_series=dividends if not dividends.empty else None, market_price_series=mkt_px)
    print({
        "mom_r12_1": mf.r12_1(),
        "mom_r6_1": mf.r6_1(),
        "mom_r3_1": mf.r3_1(),
        "mom_pct_52w_high": mf.pct_from_52w_high() if hasattr(mf, 'pct_from_52w_high') else np.nan,
        "mom_sma_ratio": mf.sma_ratio() if hasattr(mf, 'sma_ratio') else np.nan,
        "mom_macd_val": mf.macd()[0] if mf.macd()[0] is not None else np.nan,
        "mom_macd_sig": mf.macd()[1] if mf.macd()[1] is not None else np.nan,
        "mom_rsi": mf.rsi() if hasattr(mf, 'rsi') else np.nan,
        "idio_mom_log": mf.idiosyncratic_momentum_log() if hasattr(mf, 'idiosyncratic_momentum_log') else np.nan,
    })

    # Value factors
    vf = ValueFactors(ticker)
    print({
        "bp": vf.compute_attributes().get("bp"),
        "ep": vf.compute_attributes().get("ep"),
        "cfp": vf.compute_attributes().get("cfp"),
        "fcf_yield": vf.compute_attributes().get("fcf_yield"),
        "sales_ev": vf.compute_attributes().get("sales_ev"),
        "ebitda_ev": vf.compute_attributes().get("ebitda_ev"),
        "ebit_ev": vf.compute_attributes().get("ebit_ev"),
        "div_yld": vf.compute_attributes().get("div_yld"),
        "trailing_pe": vf.trailing_pe(),
        "forward_pe": vf.forward_pe(),
        "earnings_yield": vf.earnings_yield(),
        "price_to_sales": vf.price_to_sales(),
        "price_to_cashflow": vf.price_to_cashflow(),
        "free_cashflow_yield": vf.free_cashflow_yield(),
        "ev_to_ebitda": vf.ev_to_ebitda(),
        "ev_to_ebit": vf.ev_to_ebit(),
        "dividend_yield": vf.dividend_yield(),
        "peg_ratio_v": vf.peg_ratio(),
    })

    # Growth factors
    gf = GrowthFactors(ticker)
    print({
        "eps_gr": gf.eps_growth_rate(),
        "eps_cagr": gf.eps_cagr(),
        "rev_gr": gf.revenue_growth_rate(),
        "sales_trend": gf.sales_trend_growth_factor(),
        "eps_yoy": gf.eps_yoy(),
        "sales_ttm_yoy": gf.sales_ttm_yoy(),
        "ocf_ttm_yoy": gf.ocf_ttm_yoy(),
        "fcf_ttm_yoy": gf.fcf_ttm_yoy(),
        "fwd_eps_g": gf.forward_eps_growth(),
        "fwd_eps_cagr_2y": gf.forward_eps_cagr_2y(),
        "fcf_gr": gf.fcf_growth_rate(),
        "peg_ratio_g": gf.peg_ratio(),
        "roe_gr": gf.roe_growth_rate(),
        "roic_gr": gf.roic_growth_rate(),
        "bvps_gr": gf.book_value_growth_rate(),
        "ocf_gr": gf.ocf_growth_rate(),
    })

    # Quality factors
    qf = QualityFactors(ticker)
    qattrs = qf.compute_attributes()
    print({
        "roe": qattrs.get("roe"),
        "roic": qattrs.get("roic"),
        "gp_a": qattrs.get("gp_a"),
        "fcf_margin": qattrs.get("fcf_margin"),
        "accruals": qattrs.get("accruals"),
        "de": qattrs.get("de"),
        "nd_ebitda": qattrs.get("nd_ebitda"),
        "int_cover": qattrs.get("int_cover"),
        "stab": qattrs.get("stab"),
        "roe_roa": qf.return_on_assets(),
        "gross_margin": qf.gross_margin(),
        "net_margin": qf.net_margin(),
        "debt_to_equity": qf.debt_to_equity(),
        "nd_to_ebitda": qf.net_debt_to_ebitda(),
        "interest_coverage": qf.interest_coverage(),
        "quick_ratio": qf.quick_ratio(),
        "altman_z": qf.altman_z_score(),
        "accruals_ratio": qf.accruals_ratio(),
        "earnings_stability": qf.earnings_stability(),
        "eps_rev_3m": qf.eps_revision_3m(),
        "div_payout": qf.dividend_payout(),
        "asset_turnover": qf.asset_turnover(),
        "cash_conversion": qf.cash_conversion_ratio(),
        "cf_to_debt": qf.cash_flow_to_debt_ratio(),
        "roce": qf.return_on_capital_employed(),
    })

    # Volatility factors
    try:
        spy = ds.get_bulk_close_series(["SPY"], start, end).get("SPY")
        spy_series = pd.Series(spy).astype(float) if spy is not None else None
    except Exception:
        spy_series = None
    vf_vol = VolatilityFactors(price_series=close, spy_price_series=spy_series)
    print({
        "realized_vol_30d": vf_vol.realized_vol_30d(),
        "realized_vol_90d": vf_vol.realized_vol_90d(),
        "annualized_vol_252": vf_vol.annualized_volatility(252),
        "daily_vol": vf_vol.daily_return_volatility(),
        "beta_1y": vf_vol.beta_1yr(),
        "idio_vol": vf_vol.idiosyncratic_vol(),
        "downside_dev_30d": vf_vol.downside_dev_30d(),
        "downside_dev_252": vf_vol.downside_dev_252(),
        "mdd_1y": vf_vol.max_drawdown_1yr(),
        "variance_ratio_3m_12m": vf_vol.variance_ratio_3m_12m(),
        "short_long_vol_ratio": vf_vol.short_long_vol_ratio(),
        "skew": vf_vol.skewness(),
        "kurt": vf_vol.kurtosis(),
        "garch_forecast": vf_vol.garch_forecast(),
        "ewma_vol": vf_vol.ewma_vol(),
    })


if __name__ == "__main__":
    main()


