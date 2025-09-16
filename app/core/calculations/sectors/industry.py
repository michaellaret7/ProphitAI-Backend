from functools import partial
from app.core.calculations.sectors.base import create_factor_calculator

# Create all industry factor calculators using partial application
calc_industry_growth_factors = lambda industry: create_factor_calculator('growth')(industry, 'industry')
calc_industry_value_factors = lambda industry: create_factor_calculator('value')(industry, 'industry')
calc_industry_momentum_factors = lambda industry: create_factor_calculator('momentum')(industry, 'industry')
calc_industry_quality_factors = lambda industry: create_factor_calculator('quality')(industry, 'industry')
calc_industry_volatility_factors = lambda industry: create_factor_calculator('volatility')(industry, 'industry')

def calc_industry_factor_benchmark_calculations(industry: str, factor: str):
    if factor == "growth":
        return calc_industry_growth_factors(industry)
    elif factor == "value":
        return calc_industry_value_factors(industry)
    elif factor == "momentum":
        return calc_industry_momentum_factors(industry)
    elif factor == "quality":
        return calc_industry_quality_factors(industry)
    elif factor == "volatility":
        return calc_industry_volatility_factors(industry)
    else:
        raise ValueError(f"Unknown factor: {factor}")

if __name__ == "__main__":
    print(calc_industry_factor_benchmark_calculations("beverages", "growth"))
    print(calc_industry_factor_benchmark_calculations("beverages", "value"))
    print(calc_industry_factor_benchmark_calculations("beverages", "momentum"))
    print(calc_industry_factor_benchmark_calculations("beverages", "quality"))
    print(calc_industry_factor_benchmark_calculations("beverages", "volatility"))

