FROM python:3.12-alpine AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
COPY wallet-sdk/ /wallet-sdk/
COPY report-service/pyproject.toml report-service/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
WORKDIR /app
ENV PYTHONPATH=/app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /wallet-sdk /wallet-sdk
COPY report-service/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
