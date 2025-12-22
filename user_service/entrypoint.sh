#!/usr/bin/env bash
set -e

echo "Container starting with role: ${SERVICE_ROLE:-undefined}"

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

# Wait for DB if configured
if [ -n "${DB_HOST:-}" ]; then
  DB_PORT="${DB_PORT:-5432}"
  wait_for "$DB_HOST" "$DB_PORT" "Database"
fi

echo "Running migrations..."
python manage.py migrate --noinput || echo "Migration failed but continuing"

case "${SERVICE_ROLE:-web}" in
  web)
    echo "Starting Django web server..."
    python manage.py runserver 0.0.0.0:8000
    ;;
  user_consumer)
    echo "Starting USER diet RabbitMQ consumer..."
    python manage.py diet_worker
    ;;
  trainer_consumer)
    echo "Starting TRAINER RabbitMQ consumer..."
    python manage.py run_rabbit_trainer_consumer
    ;;
  *)
    echo "❌ Unknown SERVICE_ROLE: ${SERVICE_ROLE}"
    exit 1
    ;;
esac
