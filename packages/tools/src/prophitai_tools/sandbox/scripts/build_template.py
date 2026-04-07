"""Build the E2B sandbox template for strategy development.

Run this once to create the 'prophitai-strategies' template on E2B.
Requires E2B_API_KEY in your environment.

Usage:
    python packages/tools/src/prophitai_tools/sandbox/scripts/build_template.py
"""

import os

from dotenv import load_dotenv
from e2b import Template

load_dotenv()

assert os.getenv("E2B_API_KEY"), "E2B_API_KEY must be set in .env"

print("Building E2B template 'prophitai-strategies'...")

builder = (
    Template()
    .from_python_image("3.13")
    .apt_install(["git", "curl"])
    .run_cmd("curl -LsSf https://astral.sh/uv/install.sh | sh")
    .pip_install(["ruff", "psycopg2-binary"])
    .set_workdir("/home/user")
)

result = Template.build(builder, name="prophitai-strategies")
print(f"Template built successfully: {result}")
print("You can now use Sandbox(template='prophitai-strategies') in your tools.")
