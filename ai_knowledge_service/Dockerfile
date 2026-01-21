FROM python:3.11-slim

# -------------------------------------------------
# 🔥 ENV — runtime behavior control (VERY IMPORTANT)
# -------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 🔥 Force HuggingFace OFFLINE MODE
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
ENV TOKENIZERS_PARALLELISM=false

WORKDIR /app

# -------------------------------------------------
# System deps
# -------------------------------------------------
RUN apt-get update && \
    apt-get install -y build-essential curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# Python deps
# -------------------------------------------------
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# -------------------------------------------------
# 🔥 Copy MODELS into image (safety + fallback)
# -------------------------------------------------
COPY models /app/models

# -------------------------------------------------
# App code + data
# -------------------------------------------------
COPY src ./src
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
