FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV PYTHONPATH=/app
ENV UV_SYSTEM_PYTHON=1
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--reload"]
