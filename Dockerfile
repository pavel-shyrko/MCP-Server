# ---------- Build stage ----------
FROM python:3.13-slim AS builder

WORKDIR /build

# Install pip dependencies first (to leverage Docker cache)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy source code
COPY app ./app

# ---------- Final image ----------
FROM python:3.13-slim

WORKDIR /app

# Copy only installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY --from=builder /build/app ./app

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
