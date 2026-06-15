FROM python:3.12-slim

# Security: run as non-root
RUN addgroup --system waybill && adduser --system --ingroup waybill waybill

WORKDIR /app

# Install deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN chown -R waybill:waybill /app
USER waybill

EXPOSE 8000

# Migrations first, then start
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
