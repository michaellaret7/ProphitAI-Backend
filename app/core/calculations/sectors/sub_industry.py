from functools import partial
from app.core.calculations.sectors.base import create_factor_calculator
from typing import Optional
from datetime import datetime

# Create all sub-industry factor calculators using partial application
calc_sub_industry_growth_factors = lambda sub_industry, as_of_date=None: create_factor_calculator('growth')(sub_industry, 'sub_industry', as_of_date=as_of_date)
calc_sub_industry_value_factors = lambda sub_industry, as_of_date=None: create_factor_calculator('value')(sub_industry, 'sub_industry', as_of_date=as_of_date)
calc_sub_industry_momentum_factors = lambda sub_industry, as_of_date=None: create_factor_calculator('momentum')(sub_industry, 'sub_industry', as_of_date=as_of_date)
calc_sub_industry_quality_factors = lambda sub_industry, as_of_date=None: create_factor_calculator('quality')(sub_industry, 'sub_industry', as_of_date=as_of_date)
calc_sub_industry_volatility_factors = lambda sub_industry, as_of_date=None: create_factor_calculator('volatility')(sub_industry, 'sub_industry', as_of_date=as_of_date)

def calc_sub_industry_factor_benchmark_calculations(sub_industry: str, factor: str, as_of_date: Optional[datetime] = None):
    if factor == "growth":
        return calc_sub_industry_growth_factors(sub_industry, as_of_date=as_of_date)
    elif factor == "value":
        return calc_sub_industry_value_factors(sub_industry, as_of_date=as_of_date)
    elif factor == "momentum":
        return calc_sub_industry_momentum_factors(sub_industry, as_of_date=as_of_date)
    elif factor == "quality":
        return calc_sub_industry_quality_factors(sub_industry, as_of_date=as_of_date)
    elif factor == "volatility":
        return calc_sub_industry_volatility_factors(sub_industry, as_of_date=as_of_date)
    else:
        raise ValueError(f"Unknown factor: {factor}")


