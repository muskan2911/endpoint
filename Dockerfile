FROM python:3.10-slim

# Install build tools for dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Preinstall dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the port (Cloud Run uses PORT env variable, default is 8080)
ENV PORT=8080
EXPOSE 8080

# Use PORT from Cloud Run env instead of hardcoding it
CMD exec gunicorn -k uvicorn.workers.UvicornWorker main:app --bind :$PORT --timeout 90
