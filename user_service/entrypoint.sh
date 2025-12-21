#!/usr/bin/env bash
set -e

echo "Container starting with role: ${SERVICE_ROLE:-undefined}"

# helper to wait for a TCP host:port
wait_for() {
  host="$1"
  port="$2"
  name="$3"
  echo "Waiting for ${name} at ${host}:${port} ..."
  until nc -z "$host" "$port"; do
    echo "${name} not ready... retrying"
    sleep 1
  done
  echo "${name} is ready!"
}

# --------------------------
# Wait for Database (only if DB_HOST provided)
# --------------------------
if [ -n "${DB_HOST:-}" ]; then
  DB_PORT="${DB_PORT:-5432}"
  wait_for "$DB_HOST" "$DB_PORT" "Database"
fi

# --------------------------
# Wait for RabbitMQ (only if RABBIT_HOST provided)
# --------------------------
if [ -n "${RABBIT_HOST:-}" ]; then
  RABBIT_PORT="${RABBIT_PORT:-5672}"
  wait_for "$RABBIT_HOST" "$RABBIT_PORT" "RabbitMQ"
fi

# --------------------------
# Run migrations (safe for SQLite too)
# --------------------------
echo "Running migrations..."
python manage.py migrate --noinput || echo "Migration failed but continuing"

# --------------------------
# Start correct process
# --------------------------
if [ "${SERVICE_ROLE:-web}" = "consumer" ]; then
  echo "Starting RabbitMQ consumer..."
  python manage.py run_rabbit_consumer
else
  echo "Starting Django web server..."
  python manage.py runserver 0.0.0.0:8000
fi
