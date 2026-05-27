import os
from dotenv import load_dotenv

ENV = os.getenv("ENV", "local").lower()

if ENV == "local":
    load_dotenv()

class Config:
    """
    Configuración del servicio de upload
    """

    ENV = ENV

    # Google Cloud Storage
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    if not GCS_BUCKET_NAME:
        raise RuntimeError("Missing env var: GCS_BUCKET_NAME")

    # Opcional (no requerido en Cloud Run)
    GCS_PROJECT_ID = os.getenv("GCS_PROJECT_ID")

    # Upload Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 16 * 1024 * 1024))  # 16MB
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 5 * 1024 * 1024 * 1024))  # 10GB

    # Debug
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
