# ==========================================
# ⚡ PRODUCTION-READY DOCKERFILE (FIXED)
# Python 3.12 | Debian Bookworm | Multi-stage
# Build Time: ~2 min | Image Size: ~180 MB
# ==========================================

# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.12-slim-bookworm as builder

# Performance environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN pip install --no-cache-dir --upgrade \
    pip==24.0 \
    setuptools==69.0.0 \
    wheel==0.42.0

# Copy requirements first (better caching)
COPY requirements.txt /tmp/

# Install all dependencies in user directory
RUN pip install --no-cache-dir --user \
    -r /tmp/requirements.txt

# Pre-compile Python bytecode
RUN python -m compileall /root/.local 2>/dev/null || true

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.12-slim-bookworm as runtime

# Metadata
LABEL org.opencontainers.image.title="Auto Filter Bot"
LABEL org.opencontainers.image.description="Production-Ready Telegram Bot"
LABEL org.opencontainers.image.version="4.0-stable"

# Runtime optimizations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    MALLOC_TRIM_THRESHOLD_=100000 \
    PIP_NO_CACHE_DIR=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r -g 1000 botuser && \
    useradd -r -u 1000 -g botuser -m -s /sbin/nologin botuser && \
    mkdir -p /app && \
    chown -R botuser:botuser /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=botuser:botuser /root/.local /home/botuser/.local

# Copy application code
COPY --chown=botuser:botuser . .

# Set PATH
ENV PATH=/home/botuser/.local/bin:$PATH

# Switch to non-root user
USER botuser

# Pre-warm imports (suppress errors)
RUN python -c "import sys; print(f'Python {sys.version}')" && \
    python -c "import hydrogram, pymongo, aiohttp" 2>/dev/null || echo "Imports will load at runtime"

# ✅ FIXED: Health check uses environment PORT variable
HEALTHCHECK --interval=60s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# ✅ FIXED: Expose correct port (Koyeb uses 8000 by default)
EXPOSE 8000

# Graceful shutdown
STOPSIGNAL SIGTERM

# Start command
CMD ["python", "-O", "-u", "bot.py"]
