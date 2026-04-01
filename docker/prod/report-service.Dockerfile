FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV PYTHONPATH=/app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY wallet-sdk/ /wallet-sdk/
COPY report-service/pyproject.toml report-service/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY report-service/ .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
