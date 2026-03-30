FROM python:3.11-alpine

RUN apk add --no-cache git openssh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --chown=appuser:appgroup . .

USER appuser

CMD ["sh", "-c", "uvicorn main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8080} --workers ${APP_WORKERS:-1}"]
