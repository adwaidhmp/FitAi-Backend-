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

case "${SERVICE_ROLE:-web}" in

  web)
    # ---- wait for DB if configured ----
    if [ -n "${DB_HOST:-}" ]; then
      DB_PORT="${DB_PORT:-5432}"
      wait_for "$DB_HOST" "$DB_PORT" "Database"
    fi

    # 🔥 REQUIRED FOR WEBSOCKETS
    wait_for "redis" "6379" "Redis"

    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Starting ASGI server (Daphne)..."
    daphne -b 0.0.0.0 -p 8000 user_service.asgi:application
    ;;

  user_consumer)
    wait_for "rabbitmq" "5672" "RabbitMQ"
    echo "Starting USER profile RabbitMQ consumer..."
    python manage.py run_rabbit_consumer
    ;;

  trainer_consumer)
    wait_for "rabbitmq" "5672" "RabbitMQ"
    echo "Starting TRAINER RabbitMQ consumer..."
    python manage.py run_rabbit_trainer_consumer
    ;;

  celery_worker)
    wait_for "rabbitmq" "5672" "RabbitMQ"
    echo "Starting Celery worker..."
    celery -A user_service.celery worker -l info -Q user_tasks
    ;;

  *)
    echo "❌ Unknown SERVICE_ROLE: ${SERVICE_ROLE}"
    exit 1
    ;;
esac
