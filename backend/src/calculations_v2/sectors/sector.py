from functools import partial
from backend.src.calculations_v2.sectors.base import create_factor_calculator

# Create all sector factor calculators using partial application
calc_sector_growth_factors = lambda sector: create_factor_calculator('growth')(sector, 'sector')
calc_sector_value_factors = lambda sector: create_factor_calculator('value')(sector, 'sector')
calc_sector_momentum_factors = lambda sector: create_factor_calculator('momentum')(sector, 'sector')
calc_sector_quality_factors = lambda sector: create_factor_calculator('quality')(sector, 'sector')
calc_sector_volatility_factors = lambda sector: create_factor_calculator('volatility')(sector, 'sector')

if __name__ == "__main__":
    print(calc_sector_growth_factors("equity_sector_information_technology"))

