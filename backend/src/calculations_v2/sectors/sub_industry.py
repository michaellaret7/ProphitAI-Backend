from functools import partial
from backend.src.calculations_v2.sectors.base import create_factor_calculator

# Create all sub-industry factor calculators using partial application
calc_sub_industry_growth_factors = lambda sub_industry: create_factor_calculator('growth')(sub_industry, 'sub_industry')
calc_sub_industry_value_factors = lambda sub_industry: create_factor_calculator('value')(sub_industry, 'sub_industry')  
calc_sub_industry_momentum_factors = lambda sub_industry: create_factor_calculator('momentum')(sub_industry, 'sub_industry')
calc_sub_industry_quality_factors = lambda sub_industry: create_factor_calculator('quality')(sub_industry, 'sub_industry')
calc_sub_industry_volatility_factors = lambda sub_industry: create_factor_calculator('volatility')(sub_industry, 'sub_industry')

if __name__ == "__main__":
    print(calc_sub_industry_momentum_factors("semiconductors"))
    # print(calc_sub_industry_growth_factors("systems_software"))
    # print(calc_sub_industry_value_factors("semiconductors"))
