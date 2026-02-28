FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code into brain/ package
COPY __init__.py main.py ./brain/
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "uvicorn", "brain.main:app", "--host", "0.0.0.0", "--port", "8000"]
