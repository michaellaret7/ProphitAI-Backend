"""Quick test of @agent_tool decorator with docstring parsing."""

import json
from typing import Annotated, Literal, Optional
from datetime import datetime
from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.brokers.alpaca_broker.broker import ProphitBroker

broker = ProphitBroker(sandbox=True)

print(broker.get_account_activities(account_id="d27aa8c2-5931-499b-bdfa-05c47b07ad70"))