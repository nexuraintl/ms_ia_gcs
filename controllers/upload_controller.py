from flask import Blueprint, request, jsonify, current_app
from services.gcs_service import GCSService


upload_bp = Blueprint("upload", __name__)

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


@upload_bp.route("/list", methods=["GET"])
def list_files():
    """
    Lista archivos del bucket.

    Query params:
      - prefix: str (opcional)
      - max_results: int (opcional, default 20, max 100)
    """
    try:
        prefix = request.args.get("prefix", "", type=str)
        max_results = request.args.get("max_results", 20, type=int)

        if max_results > 100:
            max_results = 100
        if max_results < 1:
            max_results = 1

        gcs = GCSService()
        result = gcs.list_files(prefix=prefix, max_results=max_results)
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error en /list: {str(e)}")
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
            "health": "GET /api/health"
        },
        "note": "El archivo NO se sube al servicio. Se sube directo a GCS usando session_url."
    }), 200
