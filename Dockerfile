# Production Dockerfile for Truefu Hires DSP Backend
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system audio dependencies (FFmpeg & libsndfile for FLAC/WAV/DSD decoding)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code and tests fixtures
COPY backend/ ./backend/

# Expose server port
EXPOSE 8000

# Start FastAPI server via uvicorn
CMD python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
