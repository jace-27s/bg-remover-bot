FROM python:3.11-slim

# System deps needed by Pillow/onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Limits onnxruntime's internal thread pool — reduces peak memory usage on
# small (512MB-1GB RAM) hosts, at a small cost to inference speed.
ENV OMP_NUM_THREADS=1
ENV OMP_WAIT_POLICY=PASSIVE

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the rembg model at build time so the container starts fast
# and doesn't need network access to a model host at runtime.
RUN python -c "from rembg import new_session; new_session('isnet-general-use')"

COPY . .

CMD ["python", "bot.py"]
