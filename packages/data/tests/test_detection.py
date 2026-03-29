"""Tests for portfolio detection threshold constants and result models.

Validates threshold values and Pydantic model instantiation for
DriftResult, DrawdownResult, and PortfolioCorrelationResult.
"""

import pytest

from prophitai_data.jobs.portfolio.models import (
    DRIFT_THRESHOLD,
    DRAWDOWN_THRESHOLD,
    PORTFOLIO_CORR_HIGH_THRESHOLD,
    PORTFOLIO_CORR_ZSCORE_THRESHOLD,
    PORTFOLIO_CORR_DISPERSION_THRESHOLD,
    PRICE_TARGET_CHANGE_THRESHOLD,
    DriftDetails,
    DriftResult,
    DrawdownDetails,
    DrawdownResult,
    PortfolioCorrelationResult,
    PriceTargetChangeDetails,
    PriceTargetChangeResult,
)


class TestThresholdConstants:
    """Verify threshold constants have expected values."""

    def test_drift_threshold_value(self):
        """DRIFT_THRESHOLD is 5% (0.05)."""
        assert DRIFT_THRESHOLD == pytest.approx(0.05)

    def test_drawdown_threshold_value(self):
        """DRAWDOWN_THRESHOLD is -10% (-0.10)."""
        assert DRAWDOWN_THRESHOLD == pytest.approx(-0.10)

    def test_correlation_high_threshold(self):
        """PORTFOLIO_CORR_HIGH_THRESHOLD is 0.50."""
        assert PORTFOLIO_CORR_HIGH_THRESHOLD == pytest.approx(0.50)

    def test_correlation_zscore_threshold(self):
        """PORTFOLIO_CORR_ZSCORE_THRESHOLD is 2.0."""
        assert PORTFOLIO_CORR_ZSCORE_THRESHOLD == pytest.approx(2.0)

    def test_correlation_dispersion_threshold(self):
        """PORTFOLIO_CORR_DISPERSION_THRESHOLD is 0.15."""
        assert PORTFOLIO_CORR_DISPERSION_THRESHOLD == pytest.approx(0.15)

    def test_price_target_change_threshold(self):
        """PRICE_TARGET_CHANGE_THRESHOLD is 5% (0.05)."""
        assert PRICE_TARGET_CHANGE_THRESHOLD == pytest.approx(0.05)


class TestDriftResultModel:
    """Tests for DriftResult and DriftDetails Pydantic models."""

    def test_drift_result_no_flags(self):
        """DriftResult with empty flagged_sectors and triggered=False."""
        result = DriftResult(flagged_sectors={}, triggered=False)
        assert result.triggered is False
        assert result.flagged_sectors == {}

    def test_drift_result_with_flags(self):
        """DriftResult with flagged sectors populates all fields correctly."""
        details = DriftDetails(
            current_allocation=0.35,
            target_allocation=0.25,
            drift=0.10,
        )
        result = DriftResult(
            flagged_sectors={"Technology": details},
            triggered=True,
        )
        assert result.triggered is True
        assert result.flagged_sectors["Technology"].drift == pytest.approx(0.10)
        assert result.flagged_sectors["Technology"].current_allocation == pytest.approx(0.35)
        assert result.flagged_sectors["Technology"].target_allocation == pytest.approx(0.25)


class TestDrawdownResultModel:
    """Tests for DrawdownResult and DrawdownDetails Pydantic models."""

    def test_drawdown_result_no_flags(self):
        """DrawdownResult with empty flagged_positions and triggered=False."""
        result = DrawdownResult(flagged_positions={}, triggered=False)
        assert result.triggered is False
        assert result.flagged_positions == {}

    def test_drawdown_result_with_flags(self):
        """DrawdownResult with flagged positions populates all fields."""
        details = DrawdownDetails(
            current_drawdown=-0.15,
            max_drawdown=-0.22,
            peak_date="2026-01-10",
        )
        result = DrawdownResult(
            flagged_positions={"AAPL": details},
            triggered=True,
        )
        assert result.triggered is True
        assert result.flagged_positions["AAPL"].current_drawdown == pytest.approx(-0.15)
        assert result.flagged_positions["AAPL"].max_drawdown == pytest.approx(-0.22)
        assert result.flagged_positions["AAPL"].peak_date == "2026-01-10"


class TestPortfolioCorrelationResultModel:
    """Tests for PortfolioCorrelationResult Pydantic model."""

    def test_correlation_result_instantiation(self):
        """PortfolioCorrelationResult instantiates with all expected fields."""
        result = PortfolioCorrelationResult(
            recent_avg=0.65,
            baseline_avg=0.45,
            change=0.20,
            dispersion=0.12,
            z_score=2.5,
            trend="Rising",
            triggered=True,
        )
        assert result.recent_avg == pytest.approx(0.65)
        assert result.baseline_avg == pytest.approx(0.45)
        assert result.change == pytest.approx(0.20)
        assert result.dispersion == pytest.approx(0.12)
        assert result.z_score == pytest.approx(2.5)
        assert result.trend == "Rising"
        assert result.triggered is True

    def test_correlation_result_empty_factory(self):
        """PortfolioCorrelationResult.empty() returns default untriggered result."""
        result = PortfolioCorrelationResult.empty()
        assert result.triggered is False
        assert result.recent_avg == pytest.approx(0.0)
        assert result.baseline_avg == pytest.approx(0.0)
        assert result.trend == "N/A"

    def test_correlation_result_valid_trends(self):
        """PortfolioCorrelationResult accepts all valid trend literals."""
        for trend in ("Rising", "Stable", "Falling", "N/A"):
            result = PortfolioCorrelationResult(
                recent_avg=0.0, baseline_avg=0.0, change=0.0,
                dispersion=0.0, z_score=0.0, trend=trend, triggered=False,
            )
            assert result.trend == trend


class TestPriceTargetChangeResultModel:
    """Tests for PriceTargetChangeResult and PriceTargetChangeDetails."""

    def test_price_target_result_with_flags(self):
        """PriceTargetChangeResult with flagged positions."""
        details = PriceTargetChangeDetails(
            current_price=180.0,
            target_price=150.0,
            deviation=0.20,
        )
        result = PriceTargetChangeResult(
            flagged_positions={"AAPL": details},
            triggered=True,
        )
        assert result.triggered is True
        assert result.flagged_positions["AAPL"].current_price == pytest.approx(180.0)
        assert result.flagged_positions["AAPL"].target_price == pytest.approx(150.0)
        assert result.flagged_positions["AAPL"].deviation == pytest.approx(0.20)

    def test_price_target_result_no_flags(self):
        """PriceTargetChangeResult with no flags is untriggered."""
        result = PriceTargetChangeResult(flagged_positions={}, triggered=False)
        assert result.triggered is False
        assert result.flagged_positions == {}
