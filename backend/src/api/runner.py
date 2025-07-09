from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json, uuid, sys, io, threading, queue, asyncio, logging
from backend.src.portfolio_optimization.runner import main as run_workflow
from backend.src.auth import get_current_user

router = APIRouter()

class WorkflowResponse(BaseModel):
    success: bool
    message: str
    recommendations: Optional[Dict[str, Any]] = None

@router.post("/runner/optimize", response_model=WorkflowResponse)
async def run_optimization(current_user=Depends(get_current_user)):
    """
    Execute the full portfolio optimization workflow for the authenticated user.
    
    Runs phase-one (sector allocation) and phase-two (ticker selection),
    stores results in database, and returns final recommendations.
    
    Args:
        current_user: The authenticated user object, injected by dependency.

    Returns:
        WorkflowResponse: Object containing success status, message, and recommendations.
        
    Raises:
        HTTPException: 500 error if workflow execution fails.
    """
    try:
        user_id = current_user.id
        email = current_user.email
        
        final_recommendations = run_workflow(user_id=user_id, email=email)
        
        if final_recommendations is not None:
            # Convert UUID objects to strings for JSON serialization
            class UUIDEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, uuid.UUID):
                        return str(obj)
                    return json.JSONEncoder.default(self, obj)
            
            # Ensure recommendations can be serialized
            serializable_recommendations = json.loads(
                json.dumps(final_recommendations, cls=UUIDEncoder)
            )
            
            return WorkflowResponse(
                success=True,
                message="Portfolio optimization workflow completed successfully",
                recommendations=serializable_recommendations
            )
        else:
            return WorkflowResponse(
                success=False,
                message="Workflow did not complete successfully or was interrupted",
                recommendations=None
            )
            
    except Exception as e:
        print(f"Error in portfolio optimization workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Error running portfolio optimization workflow: {str(e)}")