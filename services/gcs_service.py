from google.cloud import storage
from flask import current_app
import uuid


class GCSService:
    """
    Servicio para GCS enfocado a resumable uploads:
    - Cloud Run genera session_url
    - El cliente sube DIRECTO a GCS usando esa URL (PUT + Content-Range)
    """

    def __init__(self):
        self.client = storage.Client()

        self.bucket_name = current_app.config["GCS_BUCKET_NAME"]
        self.bucket = self.client.bucket(self.bucket_name)

        # Toma valores del config (no hardcode)
        self.chunk_size = int(current_app.config.get("CHUNK_SIZE", 16 * 1024 * 1024))
        self.max_file_size = int(current_app.config.get("MAX_FILE_SIZE", 5 * 1024 * 1024 * 1024))

    def start_resumable_upload(self, filename: str, file_size: int, content_type: str):
        """
        Crea una sesión reanudable y devuelve session_url.
        - Solo se genera la URL temporal para que el cliente haga PUT directo a GCS.
        """
        if file_size > self.max_file_size:
            raise ValueError(
                f"Archivo excede tamaño máximo permitido: {self.max_file_size} bytes"
            )

        unique_filename = f"{uuid.uuid4()}_{filename}"

        blob = self.bucket.blob(unique_filename)

        session_url = blob.create_resumable_upload_session(
            content_type=content_type,
            size=file_size
        )

        return {
            "success": True,
            "session_url": session_url,
            "unique_filename": unique_filename,
            "original_filename": filename,
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 ** 2), 2),
            "chunk_size": self.chunk_size,
            "chunk_size_mb": round(self.chunk_size / (1024 ** 2), 2),
            "content_type": content_type,
            "bucket": self.bucket_name
        }

    def verify_file(self, filename):
        """
        Verifica si un archivo existe en GCS y obtiene su información
        """
        blob = self.bucket.blob(filename)

        if not blob.exists():
            return {
                "success": False,
                "exists": False,
                "filename": filename,
                "message": "El archivo no existe en GCS"
            }

        blob.reload()

        return {
            "success": True,
            "exists": True,
            "filename": filename,
            "size": blob.size,
            "size_mb": round(blob.size / (1024 ** 2), 2),
            "size_gb": round(blob.size / (1024 ** 3), 2),
            "content_type": blob.content_type,
            "created": blob.time_created.isoformat() if blob.time_created else None,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "md5_hash": blob.md5_hash,
            "public_url": f"gs://{self.bucket_name}/{filename}",
            "generation": blob.generation,
            "bucket": self.bucket_name
        }

    def list_files(self, prefix="", max_results=20):
        """
        Lista archivos en el bucket
        """
        blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_results)

        files = []
        total_size = 0

        for blob in blobs:
            files.append({
                "filename": blob.name,
                "size": blob.size,
                "size_mb": round(blob.size / (1024 ** 2), 2),
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "md5_hash": blob.md5_hash
            })
            total_size += blob.size

        return {
            "success": True,
            "bucket": self.bucket_name,
            "count": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 ** 2), 2),
            "total_size_gb": round(total_size / (1024 ** 3), 2),
            "files": files
        }
