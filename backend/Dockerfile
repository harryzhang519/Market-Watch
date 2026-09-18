# ── Backend Dockerfile ─────────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
