FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/requirements.txt

# Install Python requirements + eventlet (no apt-get needed)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir eventlet

COPY . /app

EXPOSE 8501

ENV FLASK_ENV=production

CMD ["python3", "socket_server.py"]
