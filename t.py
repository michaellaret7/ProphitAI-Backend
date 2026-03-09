"""Quick script to test dashboard controller output (bypasses auth)."""

import asyncio
import json
from app.api.controller.dashboard import get_dashboard_controller

CLERK_ID = "user_36g2ainRF5BuSMwadbvxAXifAYf"


async def main():
    result = await get_dashboard_controller(clerk_id=CLERK_ID)
    print(json.dumps(result, indent=2, default=str))


asyncio.run(main())
