FROM python:3.11-slim

# =========================
# Environment Optimizations
# =========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# =========================
# System Dependencies
# =========================
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Python Dependencies
# =========================
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# =========================
# Bot Source Code
# =========================
COPY . .

# =========================
# Run Bot (uvloop auto-used)
# =========================
CMD ["python", "-O", "bot.py"]
