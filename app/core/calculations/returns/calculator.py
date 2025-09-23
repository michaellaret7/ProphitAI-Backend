from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class ReturnsCalculator:
    """Pure returns utilities for a single ticker time series."""

    @staticmethod
    def daily_price_returns(close: pd.Series) -> pd.Series:
        """Simple daily price returns. Assumes split/dividend-adjusted close for price-only returns."""
        return pd.Series(close).astype(float).pct_change(fill_method=None).dropna()

    @staticmethod
    def total_returns(close: pd.Series, dividends: pd.Series | None = None) -> pd.Series:
        """
        Total simple daily returns with cash dividends (no reinvestment timing):
        r_t = (P_t - P_{t-1})/P_{t-1} + D_t / P_{t-1}
        'dividends' should be per-share cash amounts on ex-dividend dates. Zeros/missing are treated as 0.
        """
        price_ret = ReturnsCalculator.daily_price_returns(close)
        if dividends is None or dividends.empty:
            return price_ret
        c = pd.Series(close).astype(float)
        div = pd.Series(dividends).astype(float)
        div_yield = (div / c.shift(1)).reindex(price_ret.index).fillna(0.0)
        return (price_ret + div_yield).dropna()

    @staticmethod
    def annualized_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
        """CAGR from daily returns over the sample window; returns NaN for empty input."""
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        total_return = float((1.0 + r).prod() - 1.0)
        n = len(r)
        return float((1.0 + total_return) ** (trading_days / n) - 1.0)
    
    @staticmethod
    def annualized_price_return(close: pd.Series, trading_days: int = 252) -> float:
        daily_price_ret = ReturnsCalculator.daily_price_returns(close)
        return ReturnsCalculator.annualized_return(daily_price_ret, trading_days)
    
    @staticmethod
    def annualized_total_return(close: pd.Series, dividends: pd.Series | None = None, trading_days: int = 252) -> float:
        daily_total_ret = ReturnsCalculator.total_returns(close, dividends)
        return ReturnsCalculator.annualized_return(daily_total_ret, trading_days)

    @staticmethod
    def holding_period_return_price_plus_divs_cash(close: pd.Series, dividends: pd.Series | None = None) -> float:
        """
        Cash total (no reinvestment): (P_end - P_start + sum(divs)) / P_start
        """
        c = pd.Series(close).dropna().astype(float)
        if c.empty:
            return np.nan
        start, end = float(c.iloc[0]), float(c.iloc[-1])
        if start <= 0:
            return np.nan
        total_divs = float(pd.Series(dividends).dropna().sum()) if dividends is not None else 0.0
        return float(((end - start) + total_divs) / start)

    @staticmethod
    def holding_period_return_total_reinvested(close: pd.Series, dividends: pd.Series | None = None) -> float:
        """
        Reinvested total return across the period: prod(1 + total_daily_return) - 1
        """
        tr = ReturnsCalculator.total_returns(close, dividends)
        return float((1.0 + tr).prod() - 1.0) if not tr.empty else np.nan

    # Backward-compatibility alias
    @staticmethod
    def holding_period_return(close: pd.Series, dividends: pd.Series | None = None) -> float:
        return ReturnsCalculator.holding_period_return_price_plus_divs_cash(close, dividends)


class PortfolioReturnsCalculator:
    """Portfolio returns from per-ticker daily returns and weights (interpreted as daily-rebalanced)."""

    @staticmethod
    def weighted_daily_returns(
        ticker_returns: dict[str, pd.Series],
        weights: dict[str, float],
        dropna: bool = True,
        renormalize_each_day: bool = False,
        normalization: str = "gross",
    ) -> pd.Series:
        """
        Build a DataFrame of aligned returns and apply weights.
        - dropna=True: drop rows with any NaNs (keeps leverage constant).
        - renormalize_each_day=True: renormalize weights over available assets each day.
          normalization:
            - "net"   -> scale to original net exposure (sum of weights)
            - "gross" -> scale to original gross exposure (sum of absolute weights)
        """
        if not ticker_returns or not weights:
            return pd.Series(dtype=float)
        tickers = [t for t in weights if t in ticker_returns]
        if not tickers:
            return pd.Series(dtype=float)
        df_raw = pd.concat({t: pd.Series(ticker_returns[t]).astype(float) for t in tickers}, axis=1)
        if dropna:
            df = df_raw.dropna(how="any")
            mask = df.notna()  # all True after dropna; used only if renormalize_each_day
        else:
            mask = df_raw.notna()
            df = df_raw.fillna(0.0)  # treats missing as 0 return; leverage will vary unless renormalized
        w = pd.Series({t: float(weights[t]) for t in tickers})
        net_target = w.sum()
        gross_target = w.abs().sum()
        if renormalize_each_day:
            eff = mask.mul(w, axis=1)
            row_gross = eff.abs().sum(axis=1)
            if normalization == "gross":
                target = gross_target if gross_target != 0 else 1.0
            else:
                target = net_target if net_target != 0 else 1.0
            adj = eff.div(row_gross.replace(0, np.nan), axis=0) * target
            adj = adj.fillna(0.0)
            portfolio = (df * adj).sum(axis=1)
        else:
            portfolio = df.dot(w)
        return portfolio
    
    @staticmethod
    def weighted_total_returns(
        ticker_dividends: dict[str, pd.Series],
        ticker_closes: dict[str, pd.Series],
        weights: dict[str, float],
        **kwargs,
    ) -> pd.Series:
        tr = {}
        for t, _w in weights.items():
            if t in ticker_closes:
                divs = ticker_dividends.get(t)
                tr[t] = ReturnsCalculator.total_returns(ticker_closes[t], divs)
        return PortfolioReturnsCalculator.weighted_daily_returns(tr, weights, **kwargs)
    
    @staticmethod
    def annualized_price_return(
        ticker_closes: dict[str, pd.Series],
        weights: dict[str, float],
        trading_days: int = 252,
        **kwargs,
    ) -> float:
        ticker_price_returns = {t: ReturnsCalculator.daily_price_returns(ticker_closes[t])
                                for t in weights if t in ticker_closes}
        portfolio_daily = PortfolioReturnsCalculator.weighted_daily_returns(ticker_price_returns, weights, **kwargs)
        return ReturnsCalculator.annualized_return(portfolio_daily, trading_days)
    
    @staticmethod
    def annualized_total_return(
        ticker_closes: dict[str, pd.Series],
        ticker_dividends: dict[str, pd.Series],
        weights: dict[str, float],
        trading_days: int = 252,
        **kwargs,
    ) -> float:
        portfolio_daily = PortfolioReturnsCalculator.weighted_total_returns(ticker_dividends, ticker_closes, weights, **kwargs)
        return ReturnsCalculator.annualized_return(portfolio_daily, trading_days)

def plot_portfolio_returns(portfolio_daily: pd.Series, ticker_closes: dict, weights: dict):
    """Simple plotting function for portfolio returns visualization."""
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Consumer Staples Portfolio Analysis', fontsize=16, fontweight='bold')
    
    # 1. Portfolio cumulative returns
    if not portfolio_daily.empty:
        cumulative_returns = (1 + portfolio_daily).cumprod()
        axes[0, 0].plot(cumulative_returns.index, cumulative_returns.values, linewidth=2, color='blue')
        axes[0, 0].set_title('Portfolio Cumulative Returns')
        axes[0, 0].set_ylabel('Cumulative Return')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. Portfolio daily returns distribution
    if not portfolio_daily.empty:
        axes[0, 1].hist(portfolio_daily.dropna(), bins=50, alpha=0.7, color='green', edgecolor='black')
        axes[0, 1].set_title('Daily Returns Distribution')
        axes[0, 1].set_xlabel('Daily Return')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axvline(portfolio_daily.mean(), color='red', linestyle='--', label=f'Mean: {portfolio_daily.mean():.4f}')
        axes[0, 1].legend()
    
    # 3. Rolling volatility (30-day)
    if not portfolio_daily.empty:
        rolling_vol = portfolio_daily.rolling(window=30).std() * np.sqrt(252)
        axes[1, 0].plot(rolling_vol.index, rolling_vol.values, linewidth=2, color='orange')
        axes[1, 0].set_title('30-Day Rolling Volatility (Annualized)')
        axes[1, 0].set_ylabel('Volatility')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].tick_params(axis='x', rotation=45)
    
    # 4. Top 10 positions by absolute weight
    abs_weights = {ticker: abs(weight) for ticker, weight in weights.items()}
    top_10 = sorted(abs_weights.items(), key=lambda x: x[1], reverse=True)[:10]
    
    if top_10:
        tickers_top = [item[0] for item in top_10]
        weights_top = [item[1] for item in top_10]
        colors = ['red' if weights[t] < 0 else 'blue' for t in tickers_top]
        
        bars = axes[1, 1].bar(range(len(tickers_top)), weights_top, color=colors, alpha=0.7)
        axes[1, 1].set_title('Top 10 Positions by Absolute Weight')
        axes[1, 1].set_ylabel('Weight')
        axes[1, 1].set_xticks(range(len(tickers_top)))
        axes[1, 1].set_xticklabels(tickers_top, rotation=45, ha='right')
        axes[1, 1].grid(True, alpha=0.3)
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='blue', alpha=0.7, label='Long'),
                          Patch(facecolor='red', alpha=0.7, label='Short')]
        axes[1, 1].legend(handles=legend_elements)
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    portfolio1 = {"portfolio": [{"ticker": "MO", "position": "long", "thesis": "Resilient cash returns at a trough multiple; smoke-free transition progressing", "key_drivers": "Dividend growth, on! pouch share gains, pricing resilience", "allocation": 0.10028}, {"ticker": "KMB", "position": "long", "thesis": "Margin recovery and portfolio focus under Powering Care; Suzano JV creates value", "key_drivers": "Cost savings, premiumization/innovation, improved 2025 outlook", "allocation": 0.09459}, {"ticker": "INGR", "position": "long", "thesis": "Value ingredients supplier with cost-plus pass-through and mix shift to specialties", "key_drivers": "Traceability/regulatory tailwinds, specialty growth, stable FCF", "allocation": 0.095}, {"ticker": "GIS", "position": "long", "thesis": "Margin mean reversion and portfolio optimization despite near-term softness", "key_drivers": "Pet food growth, SKU rationalization, yogurt divest proceeds discipline", "allocation": 0.04037}, {"ticker": "KO", "position": "long", "thesis": "Global brand with pricing power and resilient system economics", "key_drivers": "RGM execution, innovation pipeline, international bottler leverage", "allocation": 0.08245}, {"ticker": "DG", "position": "long", "thesis": "Trade-down beneficiary with self-help; comps/margins repairing", "key_drivers": "Store remodels, delivery partnerships, shrink control", "allocation": 0.07489}, {"ticker": "BJ", "position": "long", "thesis": "Club model value with resilient membership and private label mix", "key_drivers": "Renewal rates, private label penetration, traffic", "allocation": 0.02779}, {"ticker": "PPC", "position": "long", "thesis": "Poultry margin upcycle with improved mix and cash returns", "key_drivers": "Feed cost relief, foodservice mix, capacity expansion/special dividend", "allocation": 0.07188}, {"ticker": "IPAR", "position": "long", "thesis": "Prestige fragrance compounder with asset-light model", "key_drivers": "Coach license extension, Longchamp agreement, strong FCF", "allocation": 0.06883}, {"ticker": "KDP", "position": "long", "thesis": "Margin normalization and diversified beverage categories", "key_drivers": "Pricing/mix, supply normalization, improving FCF conversion", "allocation": 0.0696}, {"ticker": "CL", "position": "long", "thesis": "Global staple with pricing power and steady organic growth", "key_drivers": "Oral care innovation, EM exposure, margin discipline", "allocation": 0.03158}, {"ticker": "KVUE", "position": "long", "thesis": "Defensive consumer health with robust FCF and pricing agility", "key_drivers": "RGM levers, TSA exit efficiencies, pipeline execution", "allocation": 0.05708}, {"ticker": "CCEP", "position": "long", "thesis": "Quality KO bottler with advantaged distribution and pricing", "key_drivers": "Local execution, pricing/mix, route-to-market strength", "allocation": 0.06676}, {"ticker": "REYN", "position": "long", "thesis": "FCF-rich packaging at a discount; deleveraging underway", "key_drivers": "Resin tailwinds, cost control, cash-led debt paydown", "allocation": 0.08154}, {"ticker": "SAM", "position": "long", "thesis": "Earnings/margin inflection with low leverage", "key_drivers": "Innovation cadence, seasonality, cost discipline", "allocation": 0.02808}, {"ticker": "ACI", "position": "long", "thesis": "Discount grocer contrarian value with improving operations", "key_drivers": "Loyalty/data monetization, supply chain self-help, mix", "allocation": 0.02046}, {"ticker": "RLX", "position": "long", "thesis": "Cash-rich ENDS player at deep value in China", "key_drivers": "Balance sheet strength, volume stabilization, shareholder returns", "allocation": 0.04158}, {"ticker": "ADM", "position": "long", "thesis": "Ag origination/crush at cycle-normal valuation", "key_drivers": "Crush spreads, merchandising, disciplined capital returns", "allocation": 0.05139}, {"ticker": "LW", "position": "long", "thesis": "Value-added frozen potatoes with pricing power to QSRs", "key_drivers": "Capacity additions, customer contracts, margin resilience", "allocation": 0.04633}, {"ticker": "HSY", "position": "short", "thesis": "Cocoa-driven margin compression with compliance cost overhang", "key_drivers": "EUDR traceability costs, COGS pressure vs pricing, valuation risk", "allocation": 0.10755}, {"ticker": "CLX", "position": "short", "thesis": "Elevated leverage and operational fragility; recovery largely priced", "key_drivers": "IT/ops spend, slower volume recovery, balance sheet risk", "allocation": 0.09972}, {"ticker": "CELH", "position": "short", "thesis": "Perfection multiple with normalization/competition risk", "key_drivers": "Shelf/promo resets, category competition, valuation de-rate", "allocation": 0.05564}, {"ticker": "ELF", "position": "short", "thesis": "Stretched valuation into tariff/execution risk", "key_drivers": "China sourcing and tariff sensitivity, integration execution", "allocation": 0.05243}, {"ticker": "EL", "position": "short", "thesis": "Travel retail reset and China softness; execution risk", "key_drivers": "Tariff headwinds, PRGP/Beauty Reimagined risk, valuation", "allocation": 0.05098}, {"ticker": "FRPT", "position": "short", "thesis": "Premium pet food with thin profitability amid promo creep", "key_drivers": "Trade-down risk, input volatility, margin sensitivity", "allocation": 0.04972}, {"ticker": "UTZ", "position": "short", "thesis": "High-multiple snacks into rising promo pressure", "key_drivers": "Private label share gains, promo intensity, input costs", "allocation": 0.06362}, {"ticker": "SFM", "position": "short", "thesis": "Rich valuation vs softening momentum and trade-down risk", "key_drivers": "Price gaps vs mass, promotional environment, elasticity", "allocation": 0.06105}, {"ticker": "VITL", "position": "short", "thesis": "Egg price normalization and private label competition risk", "key_drivers": "Dozen-pricing trends, mix pressure, margin compression", "allocation": 0.04508}, {"ticker": "COTY", "position": "short", "thesis": "Soft consumer beauty with FX/tariff headwinds and weak quality", "key_drivers": "Destocking, leverage/coverage risk, execution", "allocation": 0.04266}, {"ticker": "WDFC", "position": "short", "thesis": "Perfection multiple with slowing growth and low FCF yield", "key_drivers": "Volume elasticity, valuation re-rate, cost pressure", "allocation": 0.06675}, {"ticker": "USFD", "position": "short", "thesis": "Distributor de-rating risk as margins normalize from cycle highs", "key_drivers": "Cost volatility, operating leverage reversal, guidance risk", "allocation": 0.06316}, {"ticker": "PFGC", "position": "short", "thesis": "Thin profitability and normalization risk vs prior cycle highs", "key_drivers": "Spread compression, execution sensitivity, valuation", "allocation": 0.05801}, {"ticker": "STZ", "position": "short", "thesis": "Peak-ish margins/returns with elevated leverage; regulatory risk", "key_drivers": "TTB scrutiny, RTD exposure, earnings quality", "allocation": 0.03461}]}
    portfolio =   {"portfolio": [
    {"ticker": "ACI", "position": "long", "weight": 0.02046, "reason": "Discount grocer/value trade-down beneficiary; low correlation diversifier. Conviction: Medium"},
    {"ticker": "ADM", "position": "long", "weight": 0.039, "reason": "Ag origination/crush at cycle-normal valuation; stagflation hedge. Conviction: Medium"},
    {"ticker": "BJ", "position": "long", "weight": 0.02779, "reason": "Club model with resilient membership and private label; steady cash flow. Conviction: Medium"},
    {"ticker": "CCEP", "position": "long", "weight": 0.035, "reason": "Quality KO bottler; trimmed for USD/FX risk. Conviction: Medium"},
    {"ticker": "CL", "position": "long", "weight": 0.03158, "reason": "Global staple with pricing power; steady organic growth. Conviction: Medium"},
    {"ticker": "DG", "position": "long", "weight": 0.06, "reason": "Trade-down beneficiary with self-help; defensiveness in slowdowns. Conviction: High"},
    {"ticker": "GIS", "position": "long", "weight": 0.04037, "reason": "Margin mean reversion and portfolio optimization; defensive. Conviction: Medium"},
    {"ticker": "INGR", "position": "long", "weight": 0.083, "reason": "Value ingredients supplier; cost-plus pass-throughs; inflation resilience. Conviction: High"},
    {"ticker": "KDP", "position": "long", "weight": 0.055, "reason": "Diversified beverages with margin normalization; sticky-inflation upside. Conviction: Medium"},
    {"ticker": "KMB", "position": "long", "weight": 0.065, "reason": "Household products defensiveness; margin recovery under Powering Care. Conviction: Medium"},
    {"ticker": "KO", "position": "long", "weight": 0.048, "reason": "Pricing power and resilient system; trimmed for cluster/FX. Conviction: Medium"},
    {"ticker": "KVUE", "position": "long", "weight": 0.06, "reason": "Defensive consumer health; attractive FCF and low beta. Conviction: Medium"},
    {"ticker": "LW", "position": "long", "weight": 0.035, "reason": "Value-added frozen potatoes; pricing to QSRs; sized for stress. Conviction: Medium"},
    {"ticker": "MO", "position": "long", "weight": 0.072, "reason": "Resilient cash returns at trough multiple; low beta ballast. Conviction: High"},
    {"ticker": "PPC", "position": "long", "weight": 0.055, "reason": "Poultry upcycle and mix improvement; trimmed to cap cyclicality. Conviction: Medium"},
    {"ticker": "REYN", "position": "long", "weight": 0.073, "reason": "FCF-rich packaging; deleveraging; domestic tilt reduces FX. Conviction: Medium"},
    {"ticker": "RLX", "position": "long", "weight": 0.02, "reason": "Cash-rich ENDS player; deep value; reduced for China/regs risk. Conviction: Low"},
    {"ticker": "CELH", "position": "short", "weight": 0.035, "reason": "Perfection multiple; normalization/competition risk; capped for tail risk. Conviction: Medium"},
    {"ticker": "CLX", "position": "short", "weight": 0.04, "reason": "Leverage/operational fragility; recovery priced; hedge vs household cluster. Conviction: Medium"},
    {"ticker": "COTY", "position": "short", "weight": 0.04, "reason": "Weaker quality, FX/tariff headwinds; beauty cluster hedge. Conviction: Medium"},
    {"ticker": "EL", "position": "short", "weight": 0.035, "reason": "Travel retail reset/China softness; credit sensitivity; capped. Conviction: Medium"},
    {"ticker": "ELF", "position": "short", "weight": 0.035, "reason": "Stretched valuation; tariff/execution risk; main volatility driver capped. Conviction: Medium"},
    {"ticker": "FRPT", "position": "short", "weight": 0.035, "reason": "Premium pet food; thin profitability amid promo creep; capped. Conviction: Medium"},
    {"ticker": "HSY", "position": "short", "weight": 0.04, "reason": "Cocoa-driven margin compression; compliance cost overhang. Conviction: Medium"},
    {"ticker": "PFGC", "position": "short", "weight": 0.03, "reason": "Foodservice distributor margins normalizing; reduced to cut cluster with USFD. Conviction: Medium"},
    {"ticker": "SFM", "position": "short", "weight": 0.04, "reason": "Rich valuation vs softening momentum; trade-down headwinds. Conviction: Medium"},
    {"ticker": "STZ", "position": "short", "weight": 0.04, "reason": "Peak-ish margins/returns; leverage/regulatory risk; under cap. Conviction: Medium"},
    {"ticker": "USFD", "position": "short", "weight": 0.03, "reason": "Distributor de-rating risk as margins normalize; downsized for high corr with PFGC. Conviction: Medium"},
    {"ticker": "UTZ", "position": "short", "weight": 0.04, "reason": "High-multiple snacks into rising promo pressure; capped. Conviction: Medium"},
    {"ticker": "VITL", "position": "short", "weight": 0.04, "reason": "Egg price normalization; private label competition risk. Conviction: Medium"},
    {"ticker": "WDFC", "position": "short", "weight": 0.04, "reason": "Perfection multiple with slowing growth/low FCF yield; risk capped. Conviction: Medium"}
    ]}
    from app.utils.gpt_parser import canonical_portfolio
    portfolio = canonical_portfolio(portfolio)

    # Convert to weights dict (negative for shorts)
    weights = {}
    for ticker, meta in portfolio.items():
        if meta["position"].lower() == "short":
            weights[ticker] = -meta["allocation"]
        else:
            weights[ticker] = meta["allocation"]
    
    # Calculate portfolio metrics
    from app.repositories.price_data import get_price_data_daily, get_dividends_series
    from datetime import datetime, timedelta
    
    # Get tickers
    tickers = list(weights.keys())
    
    # Fetch price data for last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=252*2)
    
    # Get price data
    ticker_closes = {}
    ticker_dividends = {}
    
    for ticker in tickers:
        try:
            # Get daily price data
            price_data = get_price_data_daily(
                ticker, 
                start_date, 
                end_date
            )
            
            if price_data is not None and not price_data.empty:
                # Set date as index and get close prices
                price_data['date'] = pd.to_datetime(price_data['date'])
                ticker_closes[ticker] = price_data.set_index('date')['close']
                
                # Get dividends
                divs = get_dividends_series(ticker, start_date, end_date)
                ticker_dividends[ticker] = divs if not divs.empty else pd.Series(0, index=ticker_closes[ticker].index)
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    # Calculate portfolio returns
    if ticker_closes:
        # Price-only return
        ann_price_return = PortfolioReturnsCalculator.annualized_price_return(
            ticker_closes, weights, dropna=False, renormalize_each_day=True
        )
        
        # Total return (with dividends)
        ann_total_return = PortfolioReturnsCalculator.annualized_total_return(
            ticker_closes, ticker_dividends, weights, dropna=False, renormalize_each_day=True
        )
        
        # Daily returns for risk metrics
        ticker_price_returns = {
            t: ReturnsCalculator.daily_price_returns(ticker_closes[t])
            for t in weights if t in ticker_closes
        }
        portfolio_daily = PortfolioReturnsCalculator.weighted_daily_returns(
            ticker_price_returns, weights, dropna=False, renormalize_each_day=True
        )
        
        # Calculate volatility
        daily_vol = portfolio_daily.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # Calculate Sharpe (assuming 3% risk-free rate)
        # risk_free = 0.03
        sharpe = (ann_price_return) / annual_vol if annual_vol > 0 else np.nan
        
        print("=== Consumer Staples Portfolio Returns ===")
        print(f"Annualized Price Return: {ann_price_return:.2%}")
        print(f"Annualized Total Return: {ann_total_return:.2%}")
        print(f"Annualized Volatility: {annual_vol:.2%}")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Number of positions: {len(weights)}")
        print(f"Long positions: {sum(1 for w in weights.values() if w > 0)}")
        print(f"Short positions: {sum(1 for w in weights.values() if w < 0)}")
        print(f"Net exposure: {sum(weights.values()):.1%}")
        
        # Graph the portfolio returns
        plot_portfolio_returns(portfolio_daily, ticker_closes, weights)
    else:
        print("No price data available for portfolio analysis")





