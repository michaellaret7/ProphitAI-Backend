from typing import Optional
from pydantic import BaseModel

class PerformanceMetrics(BaseModel):
    """Pydantic model for performance metrics"""
    annualized_return: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    treynor_ratio: Optional[float]
    information_ratio: Optional[float]
    omega_ratio: Optional[float]
    sterling_ratio: Optional[float]
    burke_ratio: Optional[float]
    martin_ratio: Optional[float]
    kappa_ratio: Optional[float]
    beta: Optional[float]
    alpha: Optional[float]
    upside_capture: Optional[float]
    downside_capture: Optional[float]
    gain_loss_ratio: Optional[float]
    pain_index: Optional[float]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    tail_ratio: Optional[float] 