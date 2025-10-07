from fastapi import HTTPException
from typing import Dict, Any
from app.services.alts import ProphitAltsServices
from app.repositories.prophit_alts_data import get_fund_table
from app.api.response_envelope import ok_envelope

async def get_fund_final_positions_controller(fund_name: str) -> Dict[str, Any]:
    """
    Controller to handle fund final positions retrieval
    """
    try:
        # Delegate to service
        service = ProphitAltsServices(fund_name)
        data = service.get_fund_performance_data()

        return ok_envelope(
            message="Fund final positions retrieved successfully",
            kind="prophitAlts#fundPerformance",
            resource_id=fund_name,
            self_link=f"/api/alts/fund/{fund_name}/data",
            updated=data.get('updated'),
            counts=data['counts'],
            payload=data['payload'],
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def get_fund_table_controller() -> Dict[str, Any]:
    """
    Controller to handle fund table retrieval
    """
    try:
        table = get_fund_table()
        return ok_envelope(
            message="Fund table retrieved successfully",
            kind="prophitAlts#fundTable",
            resource_id="funds",
            self_link=f"/api/alts/funds",
            payload=table,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
