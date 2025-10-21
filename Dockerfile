FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /app
COPY app/* .
RUN mkdir -p data && \
    mkdir -p qrcodes && \
    groupadd -r bot && \
    useradd -r -g bot bot && \
    chown -R bot:bot /app
USER bot
CMD ["python", "main.py"]
