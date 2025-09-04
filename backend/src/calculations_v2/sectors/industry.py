from functools import partial
from backend.src.calculations_v2.sectors.base import create_factor_calculator

# Create all industry factor calculators using partial application
calc_industry_growth_factors = lambda industry: create_factor_calculator('growth')(industry, 'industry')
calc_industry_value_factors = lambda industry: create_factor_calculator('value')(industry, 'industry')
calc_industry_momentum_factors = lambda industry: create_factor_calculator('momentum')(industry, 'industry')
calc_industry_quality_factors = lambda industry: create_factor_calculator('quality')(industry, 'industry')
calc_industry_volatility_factors = lambda industry: create_factor_calculator('volatility')(industry, 'industry')

if __name__ == "__main__":
    print(calc_industry_momentum_factors("software"))

