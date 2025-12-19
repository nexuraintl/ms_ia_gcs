import os
from dotenv import load_dotenv

if os.getenv("ENV", "local").lower() == "local":
    load_dotenv()

class Config:
    """
    Configuración del servicio de upload
    """

    # Google Cloud Storage
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    if not GCS_BUCKET_NAME:
        raise RuntimeError("Missing env var: GCS_BUCKET_NAME")

    GCS_PROJECT_ID = os.getenv("GCS_PROJECT_ID")

    # Upload Settings 
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(32 * 1024 * 1024)))  
    #maximo 5gb
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(5 * 1024 * 1024 * 1024)))  

    # Debug
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
