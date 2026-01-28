FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for chromadb and building packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install CPU-only PyTorch FIRST (much smaller ~200MB vs 2GB for full torch)
# This prevents sentence-transformers from installing the full GPU version
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Clean up any cached bytecode
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find . -name "*.pyc" -delete 2>/dev/null || true

# Create data directory
RUN mkdir -p /app/data

# Railway sets PORT env variable
ENV PORT=8000
EXPOSE $PORT

# Start command
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
