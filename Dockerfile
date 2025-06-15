# Build stage for Python MCP server
FROM python:3.11-slim AS build

# Set working directory
WORKDIR /app

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY . .

# Runtime stage
FROM python:3.11-slim AS runtime

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy virtual environment from build stage
COPY --from=build /app/.venv /app/.venv

# Copy application code
COPY --from=build /app .

# Make sure we use venv
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port for FastMCP server
EXPOSE 8000

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Command to run the enhanced server with SSE transport for remote access
CMD ["python", "run_server.py"]
