FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY butalrashdy.py .

CMD ["sh", "-c", "pip install -U --no-cache-dir yt-dlp || true; exec python butalrashdy.py"]
