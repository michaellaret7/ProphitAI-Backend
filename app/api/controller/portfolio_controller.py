from fastapi import HTTPException
from typing import Dict, Any, List, Optional
import uuid
from app.repositories.portfolio_data import add_portfolio, update_portfolio, delete_portfolio
from app.repositories.user_data import get_all_user_data
from app.api.response_envelope import ok_envelope

async def get_user_portfolio_list_controller(email: str) -> Dict[str, Any]:
    """
    Controller to handle user portfolio list retrieval
    """
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        user_data = get_all_user_data(email=email)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        portfolios = user_data.get('portfolios', [])
        # Convert to camelCase keys for response
        portfolios = [{
            "name": p.get("name"),
            "portfolioId": p.get("portfolio_id"),
            "isCurrent": p.get("is_current")
            #TODO: Add returns to payload and others (refer to portfolios page)
        } for p in portfolios]
        
        counts = {
            'currentItemCount': len(portfolios),
            'itemsPerPage': len(portfolios),
            'startIndex': 1,
            'totalItems': len(portfolios),
        }
        return ok_envelope(
            message="User portfolio list retrieved successfully",
            kind="users#portfolios",
            resource_id=user_data.get('id') if isinstance(user_data, dict) else None,
            self_link=f"/api/user/portfolios?email={email}",
            counts=counts,
            payload=portfolios,
        )
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

#TODO: Get portfolio positions using the uuid 

async def create_portfolio_controller(
    *,
    email: str,
    company_name: str,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        if not company_name:
            raise HTTPException(status_code=400, detail="Company name is required")
        if not portfolio_name:
            raise HTTPException(status_code=400, detail="Portfolio name is required")
        if not positions or not isinstance(positions, list):
            raise HTTPException(status_code=400, detail="Positions must be a non-empty list")

        class Position:
            def __init__(self, ticker: str, allocation: float):
                self.ticker = ticker
                self.allocation = allocation

        position_objs = []
        for p in positions:
            ticker = p.get("ticker")
            allocation = p.get("allocation")
            if ticker is None or allocation is None:
                raise HTTPException(status_code=400, detail="Each position requires ticker and allocation")
            position_objs.append(Position(ticker=ticker, allocation=allocation))

        add_portfolio(
            portfolio=position_objs,
            company_name=company_name,
            user_email=email,
            portfolio_name=portfolio_name,
        )

        user_data = get_all_user_data(email=email)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        portfolios = user_data.get('portfolios', [])
        portfolios = [{
            "name": p.get("name"),
            "portfolioId": p.get("portfolio_id"),
            "isCurrent": p.get("is_current")
        } for p in portfolios]

        counts = {
            'currentItemCount': len(portfolios),
            'itemsPerPage': len(portfolios),
            'startIndex': 1,
            'totalItems': len(portfolios),
        }

        return ok_envelope(
            message="Portfolio created successfully",
            kind="users#portfolios",
            resource_id=user_data.get('id') if isinstance(user_data, dict) else None,
            self_link=f"/api/user/portfolios?email={email}",
            counts=counts,
            payload=portfolios,
            status=201,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def update_portfolio_controller(
    *,
    email: str,
    portfolio_id: str,
    name: Optional[str] = None,
    is_current: Optional[bool] = None,
) -> Dict[str, Any]:
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        if not portfolio_id:
            raise HTTPException(status_code=400, detail="portfolioId is required")

        updated = update_portfolio(
            email=email,
            portfolio_id=uuid.UUID(portfolio_id),
            name=name,
            is_current=is_current,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        user_data = get_all_user_data(email=email)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        portfolios = user_data.get('portfolios', [])
        portfolios = [{
            "name": p.get("name"),
            "portfolioId": p.get("portfolio_id"),
            "isCurrent": p.get("is_current")
        } for p in portfolios]

        counts = {
            'currentItemCount': len(portfolios),
            'itemsPerPage': len(portfolios),
            'startIndex': 1,
            'totalItems': len(portfolios),
        }

        return ok_envelope(
            message="Portfolio updated successfully",
            kind="users#portfolios",
            resource_id=user_data.get('id') if isinstance(user_data, dict) else None,
            self_link=f"/api/user/portfolios?email={email}",
            counts=counts,
            payload=portfolios,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def delete_portfolio_controller(
    *,
    email: str,
    portfolio_id: str,
) -> Dict[str, Any]:
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        if not portfolio_id:
            raise HTTPException(status_code=400, detail="portfolioId is required")

        deleted = delete_portfolio(
            email=email,
            portfolio_id=uuid.UUID(portfolio_id),
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        # After delete, return updated list
        user_data = get_all_user_data(email=email)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        portfolios = user_data.get('portfolios', [])
        portfolios = [{
            "name": p.get("name"),
            "portfolioId": p.get("portfolio_id"),
            "isCurrent": p.get("is_current")
        } for p in portfolios]

        counts = {
            'currentItemCount': len(portfolios),
            'itemsPerPage': len(portfolios),
            'startIndex': 1,
            'totalItems': len(portfolios),
        }

        return ok_envelope(
            message="Portfolio deleted successfully",
            kind="users#portfolios",
            resource_id=user_data.get('id') if isinstance(user_data, dict) else None,
            self_link=f"/api/user/portfolios?email={email}",
            counts=counts,
            payload=portfolios,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")