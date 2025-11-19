# Stage 1 - Frontend build
FROM node:20 AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend .
RUN npm run build

# Stage 2 - Backend build
FROM astral/uv:python3.13-bookworm-slim AS backend-builder
WORKDIR /app
# Install deps
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Stage 3 — Runtime image
FROM python:3.13-slim AS runtime
WORKDIR /
ARG VERSION

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor curl docker-cli \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Frontend
COPY --from=frontend-builder /app/dist/tugtainer/browser /app/frontend

# Backend, agent, shared
COPY backend /app/backend
COPY agent /app/agent
COPY shared /app/shared

# Python deps
COPY --from=backend-builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Configs
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment
COPY .env* /app/
RUN echo "$VERSION" > /app/version

# Dir for sqlite and other files
RUN mkdir -p /tugtainer && chmod 700 /tugtainer

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/public/health || exit 1

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
