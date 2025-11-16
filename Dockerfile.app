# Stage 1 - frontend build
FROM node:20 AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend .
RUN npm run build

# Stage 2 - backend build
FROM python:3.13 AS backend-builder
WORKDIR /app
RUN pip install --upgrade pip setuptools
# backend
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
# agent
COPY agent/requirements.txt agent/requirements.txt
RUN pip install --no-cache-dir -r agent/requirements.txt
COPY agent ./agent
COPY shared ./shared

# Stage 3 - container build
FROM python:3.13-slim AS runtime
WORKDIR /

ARG VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor curl docker-cli \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=frontend-builder /app/dist/tugtainer/browser /app/frontend
COPY --from=backend-builder /app/backend /app/backend
COPY --from=backend-builder /app/agent /app/agent
COPY --from=backend-builder /app/shared /app/shared
COPY --from=backend-builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=backend-builder /usr/local/bin /usr/local/bin
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY .env* /app/
RUN echo "$VERSION" > /app/version

# Dir for sqlite and other files
RUN mkdir -p /tugtainer && chmod 700 /tugtainer

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/public/health || exit 1

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]