from functools import partial
from app.core.calculations.sectors.base import create_factor_calculator
from typing import Optional
from datetime import datetime

# Create all industry factor calculators using partial application
calc_industry_growth_factors = lambda industry, as_of_date=None: create_factor_calculator('growth')(industry, 'industry', as_of_date=as_of_date)
calc_industry_value_factors = lambda industry, as_of_date=None: create_factor_calculator('value')(industry, 'industry', as_of_date=as_of_date)
calc_industry_momentum_factors = lambda industry, as_of_date=None: create_factor_calculator('momentum')(industry, 'industry', as_of_date=as_of_date)
calc_industry_quality_factors = lambda industry, as_of_date=None: create_factor_calculator('quality')(industry, 'industry', as_of_date=as_of_date)
calc_industry_volatility_factors = lambda industry, as_of_date=None: create_factor_calculator('volatility')(industry, 'industry', as_of_date=as_of_date)

def calc_industry_factor_benchmark_calculations(industry: str, factor: str, as_of_date: Optional[datetime] = None):
    if factor == "growth":
        return calc_industry_growth_factors(industry, as_of_date=as_of_date)
    elif factor == "value":
        return calc_industry_value_factors(industry, as_of_date=as_of_date)
    elif factor == "momentum":
        return calc_industry_momentum_factors(industry, as_of_date=as_of_date)
    elif factor == "quality":
        return calc_industry_quality_factors(industry, as_of_date=as_of_date)
    elif factor == "volatility":
        return calc_industry_volatility_factors(industry, as_of_date=as_of_date)
    else:
        raise ValueError(f"Unknown factor: {factor}")

if __name__ == "__main__":
    print(calc_industry_factor_benchmark_calculations("beverages", "growth"))
    print(calc_industry_factor_benchmark_calculations("beverages", "value"))
    print(calc_industry_factor_benchmark_calculations("beverages", "momentum"))
    print(calc_industry_factor_benchmark_calculations("beverages", "quality"))
    print(calc_industry_factor_benchmark_calculations("beverages", "volatility"))

