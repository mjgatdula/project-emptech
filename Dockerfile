FROM node:24-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=backend.production_settings
WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /build/dist /app/frontend/dist
RUN useradd --create-home tipped && mkdir -p /data/private_media /app/backend/staticfiles && chown -R tipped:tipped /data /app
USER tipped
EXPOSE 8000
# Container liveness is TCP-only; monitor /api/health/ready/ through the real HTTPS host.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), timeout=3).close()"
CMD ["sh", "-c", "python manage.py collectstatic --noinput && waitress-serve --listen=0.0.0.0:8000 --max-request-body-size=20971520 --trusted-proxy=${TRUSTED_PROXY_IP:?Set TRUSTED_PROXY_IP to the HTTPS reverse proxy address} --trusted-proxy-headers=x-forwarded-proto backend.wsgi:application"]
