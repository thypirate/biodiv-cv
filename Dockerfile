FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies first, so a code change does not re-resolve the lock file.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY static ./static

ENV PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/health', timeout=4)"

# Shell form on purpose: Railway (and Fly, Render, Cloud Run) inject the port to
# listen on as $PORT, and an exec-form CMD would pass the literal string
# "$PORT". Falls back to 8000 for local `docker run`.
#
# One process, no sidecars. The TTL cache lives in memory, so each replica warms
# its own — scale with replicas, not with workers inside one container.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
