from functools import partial
from backend.src.calculations_v2.sectors.base import create_factor_calculator

# Create all sub-industry factor calculators using partial application
calc_sub_industry_growth_factors = lambda sub_industry: create_factor_calculator('growth')(sub_industry, 'sub_industry')
calc_sub_industry_value_factors = lambda sub_industry: create_factor_calculator('value')(sub_industry, 'sub_industry')  
calc_sub_industry_momentum_factors = lambda sub_industry: create_factor_calculator('momentum')(sub_industry, 'sub_industry')
calc_sub_industry_quality_factors = lambda sub_industry: create_factor_calculator('quality')(sub_industry, 'sub_industry')
calc_sub_industry_volatility_factors = lambda sub_industry: create_factor_calculator('volatility')(sub_industry, 'sub_industry')

def calc_sub_industry_factor_benchmark_calculations(sub_industry: str, factor: str):
    if factor == "growth":
        return calc_sub_industry_growth_factors(sub_industry)
    elif factor == "value":
        return calc_sub_industry_value_factors(sub_industry)
    elif factor == "momentum":
        return calc_sub_industry_momentum_factors(sub_industry)
    elif factor == "quality":
        return calc_sub_industry_quality_factors(sub_industry)
    elif factor == "volatility":
        return calc_sub_industry_volatility_factors(sub_industry)
    else:
        raise ValueError(f"Unknown factor: {factor}")


