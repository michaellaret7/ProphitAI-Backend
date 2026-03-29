FROM python:3.13-slim

WORKDIR /app

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    libdbus-1-3 libatspi2.0-0 libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY . .

# Install Python deps + Playwright browser
RUN uv sync --no-editable && uv run playwright install chromium

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "prophitai_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
