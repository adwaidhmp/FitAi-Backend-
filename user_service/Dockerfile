# trainer_service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps needed for psycopg2 and building wheels
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev gcc netcat-openbsd && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy python deps and install
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy app code
COPY . .

# Copy and make entrypoint executable (expects entrypoint.sh present in repo)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["web"]
