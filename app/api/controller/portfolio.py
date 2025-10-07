from fastapi import HTTPException
from typing import Dict, Any, List, Optional
from app.services.portfolio import PortfolioService
from app.services.portfolio_returns import PortfolioReturnsService
from app.api.response_envelope import ok_envelope

async def create_portfolio_controller(
    *,
    email: str,
    company_name: str,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Controller to handle portfolio creation
    """
    try:
        # Delegate to service
        service = PortfolioService()
        data = service.create_portfolio(
            email=email,
            company_name=company_name,
            portfolio_name=portfolio_name,
            positions=positions
        )

        return ok_envelope(
            message="Portfolio created successfully",
            kind="users#portfolios",
            resource_id=data['user_data'].get('id'),
            self_link=f"/api/user/portfolios?email={email}",
            counts=data['counts'],
            payload=data['portfolios'],
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
    """
    Controller to handle portfolio updates
    """
    try:
        # Delegate to service
        service = PortfolioService()
        data = service.update_portfolio(
            email=email,
            portfolio_id=portfolio_id,
            name=name,
            is_current=is_current
        )

        return ok_envelope(
            message="Portfolio updated successfully",
            kind="users#portfolios",
            resource_id=data['user_data'].get('id'),
            self_link=f"/api/user/portfolios?email={email}",
            counts=data['counts'],
            payload=data['portfolios'],
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
    """
    Controller to handle portfolio deletion
    """
    try:
        # Delegate to service
        service = PortfolioService()
        data = service.delete_portfolio(
            email=email,
            portfolio_id=portfolio_id
        )

        return ok_envelope(
            message="Portfolio deleted successfully",
            kind="users#portfolios",
            resource_id=data['user_data'].get('id'),
            self_link=f"/api/user/portfolios?email={email}",
            counts=data['counts'],
            payload=data['portfolios'],
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def get_portfolio_returns_controller(
    *,
    portfolio_id: str,
    years: int = 2,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio returns calculation
    """
    try:
        if not portfolio_id:
            raise HTTPException(status_code=400, detail="portfolioId is required")

        # Delegate to service
        service = PortfolioReturnsService(
            portfolio_id=portfolio_id,
            years=years
        )
        returns_data = service.get_returns_series()

        return ok_envelope(
            message="Portfolio returns retrieved successfully",
            kind="portfolio#returns",
            resource_id=portfolio_id,
            self_link=f"/api/portfolio/returns?portfolioId={portfolio_id}",
            payload=returns_data,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def get_user_portfolio_list_controller(email: str = "michaellaret7@gmail.com") -> Dict[str, Any]:
    """
    Controller to handle user portfolio list retrieval
    """
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        # Delegate to service
        service = PortfolioService()
        data = service.get_user_portfolios(email=email)

        return ok_envelope(
            message="User portfolio list retrieved successfully",
            kind="users#portfolios",
            resource_id=data['user_data'].get('id'),
            self_link=f"/api/user/portfolios?email={email}",
            counts=data['counts'],
            payload=data['portfolios'],
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
