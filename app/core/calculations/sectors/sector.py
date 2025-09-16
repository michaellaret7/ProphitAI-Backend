from functools import partial
from app.core.calculations.sectors.base import create_factor_calculator

# Create all sector factor calculators using partial application
calc_sector_growth_factors = lambda sector: create_factor_calculator('growth')(sector, 'sector')
calc_sector_value_factors = lambda sector: create_factor_calculator('value')(sector, 'sector')
calc_sector_momentum_factors = lambda sector: create_factor_calculator('momentum')(sector, 'sector')
calc_sector_quality_factors = lambda sector: create_factor_calculator('quality')(sector, 'sector')
calc_sector_volatility_factors = lambda sector: create_factor_calculator('volatility')(sector, 'sector')

def calc_sector_factor_benchmark_calculations(sector: str, factor: str):
    if factor == "growth":
        return calc_sector_growth_factors(sector)
    elif factor == "value":
        return calc_sector_value_factors(sector)
    elif factor == "momentum":
        return calc_sector_momentum_factors(sector)
    elif factor == "quality":
        return calc_sector_quality_factors(sector)
    elif factor == "volatility":
        return calc_sector_volatility_factors(sector)
    else:
        raise ValueError(f"Unknown factor: {factor}")

