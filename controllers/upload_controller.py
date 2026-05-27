from flask import Blueprint, request, jsonify, current_app
from services.gcs_service import GCSService

upload_bp = Blueprint("upload", __name__)


# crear session_url
@upload_bp.route("/start-upload", methods=["POST"])
def start_upload():
    """
    Crea una sesión de carga reanudable en GCS y devuelve session_url.

    Body (JSON):
      - filename: str (requerido)
      - file_size: int (requerido, bytes)
      - content_type: str (opcional)
    """
    try:
        data = request.get_json(silent=True) or {}

        filename = data.get("filename")
        file_size = data.get("file_size")
        content_type = data.get("content_type", "application/octet-stream")

        if not filename or not str(filename).strip():
            return jsonify({"error": "filename es requerido"}), 400

        if file_size is None:
            return jsonify({"error": "file_size es requerido"}), 400

        try:
            file_size = int(file_size)
        except (TypeError, ValueError):
            return jsonify({"error": "file_size debe ser un entero"}), 400

        if file_size <= 0:
            return jsonify({"error": "file_size debe ser > 0"}), 400

        max_size = current_app.config.get("MAX_FILE_SIZE")
        if max_size and file_size > int(max_size):
            return jsonify({
                "error": f"Archivo excede tamaño máximo permitido: {max_size} bytes"
            }), 400

        gcs = GCSService()
        result = gcs.start_resumable_upload(
            filename=filename,
            file_size=file_size,
            content_type=content_type
        )

        current_app.logger.info(
            f"Resumable session creada: {result.get('unique_filename')} ({file_size} bytes)"
        )
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error en /start-upload: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =========================
# Verificar si existe un objeto
# =========================
@upload_bp.route("/comprobar", methods=["POST"])
def verify_upload():
    """
    Verifica si un archivo existe en GCS.

    Body (JSON):
      - filename: str (requerido)
    """
    try:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename")

        if not filename or not str(filename).strip():
            return jsonify({"error": "filename es requerido"}), 400

        gcs = GCSService()
        result = gcs.verify_file(filename)

        if result.get("exists"):
            current_app.logger.info(f"Archivo verificado: {filename}")
            return jsonify(result), 200

        return jsonify(result), 404

    except Exception as e:
        current_app.logger.error(f"Error en /comprobar: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Listar objetos del bucket
@upload_bp.route("/list", methods=["GET"])
def list_files():
    """
    Lista archivos del bucket.

    Query params:
      - prefix: str (opcional)
      - max_results: int (opcional, default 20, max 200)
    """
    try:
        prefix = request.args.get("prefix", "", type=str)
        max_results = request.args.get("max_results", 20, type=int)

        if max_results > 200:
            max_results = 200
        if max_results < 1:
            max_results = 1

        gcs = GCSService()
        result = gcs.list_files(prefix=prefix, max_results=max_results)
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error en /list: {str(e)}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/download-url", methods=["GET"])
def get_download_url():
    """
    Genera una URL firmada (temporal) para descargar desde GCS sin pasar por Cloud Run.

    Query params:
      - name: str (requerido) -> nombre exacto del objeto en el bucket
      - expires: int (opcional) -> segundos (default 900, min 60, max 3600)
    """
    try:
        name = request.args.get("name", type=str)
        if not name or not name.strip():
            return jsonify({"error": "name es requerido (nombre del objeto en el bucket)"}), 400

        expires = request.args.get("expires", 900, type=int)
        if expires < 60:
            expires = 60
        if expires > 3600:
            expires = 3600

        gcs = GCSService()
        result = gcs.generate_download_signed_url(object_name=name, expires_in=expires)
        return jsonify(result), (200 if result.get("success") else 404)

    except Exception as e:
        current_app.logger.error(f"Error en /download-url: {str(e)}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@upload_bp.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "GCS Resumable Upload Gateway",
        "status": "running",
        "endpoints": {
            "start_upload": "POST /api/start-upload",
            "verify": "POST /api/comprobar",
            "list": "GET /api/list?prefix=&max_results=",
            "download_url": "GET /api/download-url?name=...&expires=900",
            "health": "GET /api/health"
        },
        "note": "El archivo NO se sube al servicio. Se sube directo a GCS usando session_url."
    }), 200