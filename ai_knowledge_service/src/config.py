import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_PATH = BASE_DIR / "data" / "vector_db"
COLLECTION_NAME = "fitness_docs"