"""
Clerk Webhook Handler

Receives webhook events from Clerk for user lifecycle events.
Keeps local database in sync with Clerk.
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException
from svix.webhooks import Webhook, WebhookVerificationError
from app.repositories.user_data import (
    add_user,
    delete_user_by_clerk_id,
    assign_user_to_company_by_id,
)

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["🪝Webhooks"])

CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET")
DEFAULT_COMPANY_ID = "c13abf69-e3ff-49b1-95a7-030c1bbef7af"

@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    """
    Handle Clerk webhook events.

    Supported events:
    - user.created: Creates user in local database
    - user.deleted: Removes user from local database
    """
    if not CLERK_WEBHOOK_SECRET:
        logger.error("CLERK_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    payload = await request.body()
    headers = dict(request.headers)

    # Verify webhook signature
    wh = Webhook(CLERK_WEBHOOK_SECRET)

    try:
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type")
    data = event.get("data", {})

    logger.info(f"Received Clerk webhook: {event_type}")

    if event_type == "user.created":
        clerk_id = data.get("id")
        email = data.get("email_addresses", [{}])[0].get("email_address")
        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""

        if clerk_id and email:
            created = add_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                clerk_id=clerk_id,
            )
            if created:
                logger.info(f"Created user: {email} (clerk_id: {clerk_id})")
                # Auto-assign to default company
                assign_user_to_company_by_id(
                    email=email,
                    company_id=DEFAULT_COMPANY_ID,
                    role='member'
                )
            else:
                logger.warning(f"Failed to create user: {email}")

    elif event_type == "user.deleted":
        clerk_id = data.get("id")
        if clerk_id:
            deleted = delete_user_by_clerk_id(clerk_id=clerk_id)
            if deleted:
                logger.info(f"Deleted user with clerk_id: {clerk_id}")
            else:
                logger.warning(f"User not found for clerk_id: {clerk_id}")

    return {"status": "ok"}