# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Python dependencies before copying app code
# (layer is cached unless requirements.txt changes)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# Copy application code
COPY . /app

# Create non-privileged user and set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    # Keep instance folder writable for SQLite DB and uploads
    chmod -R 775 /app/instance

# Switch to non-privileged user
USER appuser

# Port must match FLASK_PORT in .env and the docker-compose mapping
ENV FLASK_ENV=production \
    GUNICORN_CMD_ARGS="--workers=2 --threads=2 --bind=0.0.0.0:8424 --timeout=60 --access-logfile -"

EXPOSE 8424

# Health check so docker-compose ps shows a real status
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8424/')" || exit 1

CMD ["gunicorn", "main:app"]
