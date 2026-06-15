FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ .

# Non-root user
RUN useradd -u 1001 -r -g root appuser && \
    chown -R appuser:root /app
USER 1001

EXPOSE 8080

CMD ["python", "main.py"]
