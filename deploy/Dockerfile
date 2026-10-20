# syntax=docker/dockerfile:1
# Multi-arch build: linux/amd64 for laptops, linux/arm64 for AWS Graviton.
#   docker buildx build --platform linux/arm64 -t panelscan-agent:arm64 deploy/
# The context is the repository root (see deploy/build_and_push.sh).
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENCV_OPENCL_RUNTIME=disabled \
    OMP_NUM_THREADS=2

WORKDIR /app

# libgl/libglib are not needed: opencv-python-headless is headless-only.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tests/ ./tests/
COPY results/eval.json ./results/eval.json

RUN useradd --create-home --uid 10001 inspector
USER inspector

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=2)"

CMD ["python", "-m", "uvicorn", "src.service:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
