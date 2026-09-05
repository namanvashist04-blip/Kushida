FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    ffmpeg \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip uninstall -y discord.py || true
RUN pip install --no-cache-dir --force-reinstall "py-cord[voice]>=2.6.0" PyNaCl>=1.5.0

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["python", "main.py"]
