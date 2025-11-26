"""
Macro Data Update Orchestrator

This module coordinates updates for all macro data tables:
- Commodity prices
- Economic indicators
- Economic calendar

Each updater class is in its own module for better organization.
"""

from app.db.jobs.macro_jobs.commodity_prices_update import UpdateCommodityPrices
from app.db.jobs.macro_jobs.economic_indicators_update import UpdateEconomicIndicators
from app.db.jobs.macro_jobs.economic_calendar_update import UpdateEconomicCalendar


def update_all_macro_data():
    """
    Main orchestrator function to update all macro data tables.

    Returns:
        Dictionary with results from all updaters
    """
    results = {}

    # Update commodity prices
    print("\n" + "=" * 80)
    print("UPDATING COMMODITY PRICES")
    print("=" * 80 + "\n")
    try:
        commodity_updater = UpdateCommodityPrices()
        results['commodities'] = commodity_updater.update_all_commodities()
    except Exception as e:
        print(f"Fatal error updating commodity prices: {e}")
        results['commodities'] = {'error': str(e)}

    # Update economic indicators
    print("\n" + "=" * 80)
    print("UPDATING ECONOMIC INDICATORS")
    print("=" * 80 + "\n")
    try:
        indicator_updater = UpdateEconomicIndicators()
        results['indicators'] = indicator_updater.update_all_indicators()
    except Exception as e:
        print(f"Fatal error updating economic indicators: {e}")
        results['indicators'] = {'error': str(e)}

    # Update economic calendar
    print("\n" + "=" * 80)
    print("UPDATING ECONOMIC CALENDAR")
    print("=" * 80 + "\n")
    try:
        calendar_updater = UpdateEconomicCalendar()
        results['calendar'] = calendar_updater.update_with_summary()
    except Exception as e:
        print(f"Fatal error updating economic calendar: {e}")
        results['calendar'] = {'error': str(e)}

    # Print final summary
    print("\n" + "=" * 80)
    print("MACRO DATA UPDATE COMPLETE")
    print("=" * 80)
    print(f"Commodity Prices: {'SUCCESS' if results['commodities'].get('success', True) else 'FAILED'}")
    print(f"Economic Indicators: {'SUCCESS' if results['indicators'].get('success', True) else 'FAILED'}")
    print(f"Economic Calendar: {'SUCCESS' if results['calendar'].get('success', False) else 'FAILED'}")
    print("=" * 80 + "\n")

    return results


def main():
    """Main entry point for the script"""
    try:
        results = update_all_macro_data()
        return results
    except Exception as e:
        print(f"Fatal error in macro data update: {e}")
        raise


if __name__ == "__main__":
    main()
