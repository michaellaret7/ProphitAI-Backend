from fastapi import HTTPException
from typing import Dict, Any
import json
from backend.src.services.prophit_alts_service import get_fund_landing_page_metrics
from backend.src.repositories.prophit_alts_data import get_fund_final_positions
from backend.src.api.response_envelope import ok_envelope

async def get_fund_final_positions_controller(fund_name: str) -> Dict[str, Any]:
    """
    Controller to handle fund final positions retrieval
    """
    try:
        positions = get_fund_final_positions(fund_name=fund_name)
        # Filter out fields not needed in API response
        fields_to_exclude = {"id", "fund_id", "ticker_id", "reasoning", "date_created", "date_updated"}
        filtered_positions = [
            {k: v for k, v in position.items() if k not in fields_to_exclude}
            for position in positions
        ]
        # Ensure numeric allocation fields with rounding (no string formatting)
        for p in filtered_positions:
            for key in ('risk_allocation', 'portfolio_allocation'):
                if key in p and p[key] is not None:
                    try:
                        p[key] = round(float(p[key]), 3)
                    except (ValueError, TypeError):
                        pass

        # Parse metrics JSON into an object for API response
        metrics_raw = get_fund_landing_page_metrics(fund_name=fund_name)
        try:
            metrics = json.loads(metrics_raw) if isinstance(metrics_raw, str) else metrics_raw
        except Exception:
            metrics = {}

        # Convert positions to camelCase keys
        positions_camel = []
        for p in filtered_positions:
            positions_camel.append({
                'tickerName': p.get('ticker_name'),
                'position': p.get('position'),
                'industry': p.get('industry'),
                'riskAllocation': p.get('risk_allocation'),
                'portfolioAllocation': p.get('portfolio_allocation')
            })

        # Convert metrics keys to camelCase (if present)
        if isinstance(metrics, dict) and metrics:
            key_map = {
                'ytd_return': 'ytdReturn',
                'gross_exposure': 'grossExposure',
                'net_exposure': 'netExposure',
                'sharpe_ratio': 'sharpeRatio',
                'sortino_ratio': 'sortinoRatio',
                'max_drawdown': 'maxDrawdown',
                'beta': 'beta',
                'up_capture': 'upCapture',
                'down_capture': 'downCapture',
                'var_95': 'var95',
                'rolling_12m_returns_daily': 'rolling12mReturnsDaily',
                'monthly_return_history': 'monthlyReturnHistory',
                'underwater_daily': 'underwaterDaily',
                'nav_performance_daily': 'navPerformanceDaily',
                'return_distribution': 'returnDistribution'
            }
            metrics_camel = {}
            for k, v in metrics.items():
                new_k = key_map.get(k, k)
                metrics_camel[new_k] = v
            # Normalize histogram keys inside returnDistribution
            if isinstance(metrics_camel.get('returnDistribution'), list):
                rd = []
                for b in metrics_camel['returnDistribution']:
                    if isinstance(b, dict):
                        rd.append({
                            'binStart': b.get('bin_start') if 'bin_start' in b else b.get('binStart'),
                            'binEnd': b.get('bin_end') if 'bin_end' in b else b.get('binEnd'),
                            'count': b.get('count')
                        })
                    else:
                        rd.append(b)
                metrics_camel['returnDistribution'] = rd
        else:
            metrics_camel = metrics

        # Extract time-series keys from metrics so they only appear once in payload
        series_keys = {
            'navPerformanceDaily',
            'returnDistribution',
            'rolling12mReturnsDaily',
            'monthlyReturnHistory',
            'underwaterDaily',
        }
        series = {}
        if isinstance(metrics_camel, dict) and metrics_camel:
            for sk in list(series_keys):
                if sk in metrics_camel:
                    series[sk] = metrics_camel.pop(sk)

        # Build calculated data items array for counts
        calc_items = []
        if isinstance(metrics_camel, dict) and metrics_camel:
            calc_items.append({ 'type': 'metrics', 'data': dict(metrics_camel) })
        for sk, sv in series.items():
            if isinstance(sv, list):
                calc_items.append({ 'type': sk, 'data': sv })
        
        if not filtered_positions:
            raise HTTPException(
                status_code=404, 
                detail=f"No final positions found for fund: {fund_name}"
            )
        
        # Envelope metadata
        nav_series = series.get('navPerformanceDaily') if isinstance(series, dict) else None
        last_date = nav_series[-1].get('date') if isinstance(nav_series, list) and len(nav_series) > 0 else None
        counts = {
            'currentItemCount': len(calc_items),
            'itemsPerPage': len(calc_items),
            'startIndex': 1,
            'totalItems': len(calc_items),
        }

        return ok_envelope(
            message="Fund final positions retrieved successfully",
            kind="prophitAlts#fundPerformance",
            resource_id=fund_name,
            self_link=f"/api/prophit-alts/fund/{fund_name}/performance-data",
            updated=(f"{last_date}T00:00:00Z" if last_date else None),
            counts=counts,
            payload={
                "metrics": metrics_camel,
                "performanceData": positions_camel,
                **series,
            },
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

 