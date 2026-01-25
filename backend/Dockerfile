FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for chromadb
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env variable
ENV PORT=8000
EXPOSE $PORT

# Start command - use shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
