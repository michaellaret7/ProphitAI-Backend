import json
from fastapi import HTTPException
from typing import Dict, Any
from backend.src.services.prophit_alts_service import get_fund_landing_page_metrics
from backend.src.repositories.prophit_alts_data import get_fund_final_positions

async def get_fund_final_positions_controller(fund_name: str) -> Dict[str, Any]:
    """
    Controller to handle fund final positions retrieval
    """
    try:
        positions = get_fund_final_positions(fund_name=fund_name)
        
        if not positions:
            raise HTTPException(
                status_code=404, 
                detail=f"No final positions found for fund: {fund_name}"
            )
        
        return {
            "status": 200,
            "data": positions,
            "message": "Fund final positions retrieved successfully"
        }
    
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

async def get_fund_landing_page_metrics_controller(fund_name: str) -> Dict[str, Any]:
    """
    Controller to handle fund landing page metrics retrieval.
    Returns YTD return, gross/net exposure, Sharpe/Sortino ratios, max drawdown, beta, and VaR.
    """
    
    try:
        metrics = get_fund_landing_page_metrics(fund_name=fund_name)
        
        # Parse JSON response from service
        metrics_data = json.loads(metrics)
        
        # Check for error in metrics
        if "error" in metrics_data:
            raise HTTPException(
                status_code=404,
                detail=metrics_data["error"]
            )
        
        return {
            "status": 200,
            "data": metrics_data,
            "message": "Fund metrics retrieved successfully"
        }
    
    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing metrics data: {str(e)}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )