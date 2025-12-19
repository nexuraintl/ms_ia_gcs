from flask import Blueprint, request, jsonify, current_app
from ..services.gcs_service import GCSService

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/subir', methods=['POST'])
def upload_chunked():
    """
    Sube archivo Y lo divide automáticamente en chunks
    El usuario solo envía el archivo.
    """
    try:
        # Validar que hay archivo
        if 'file' not in request.files:
            return jsonify({
                'error': 'No se encontró archivo'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        # Obtener tamaño
        file.seek(0, 2)  
        file_size = file.tell()
        file.seek(0)  
        
        current_app.logger.info(f"Recibido archivo: {file.filename} ({file_size} bytes)")
        
        # Validar tamaño
        max_size = current_app.config['MAX_FILE_SIZE']
        if file_size > max_size:
            return jsonify({
                'error': f'Archivo excede tamaño máximo: {max_size} bytes'
            }), 400
        
        # Subir en chunks
        gcs = GCSService()
        result = gcs.upload_in_chunks_auto(
            file=file,
            filename=file.filename,
            content_type=file.content_type or 'application/octet-stream'
        )
        
        current_app.logger.info(f"Upload completado: {result['unique_filename']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f'Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/cargararchivo', methods=['POST'])
def upload_direct():
    """
    Sube archivo directamente SIN chunks     
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'error': 'No se encontró archivo',
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        max_size = current_app.config['MAX_FILE_SIZE']
        if file_size > max_size:
            return jsonify({
                'error': f'Archivo excede tamaño máximo: {max_size} bytes'
            }), 400
        
        gcs = GCSService()
        result = gcs.upload_file_directly(file)
        
        current_app.logger.info(f"Archivo subido: {result['unique_filename']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f'Error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/comprobar', methods=['POST'])
def verify_upload():
    """
    Verifica si el archivo se subió correctamente
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Body vacío'}), 400
        
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'nombre de archivo requerido'}), 400
        
        gcs = GCSService()
        result = gcs.verify_file(filename)
        
        if result['exists']:
            current_app.logger.info(f"Archivo verificado: {filename}")
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except Exception as e:
        current_app.logger.error(f'Error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/list', methods=['GET'])
def list_files():
    """
    Lista archivos en el bucket
    """
    try:
        max_results = request.args.get('max_results', 20, type=int)
        prefix = request.args.get('prefix', '')
        
        if max_results > 100:
            max_results = 100
        
        gcs = GCSService()
        result = gcs.list_files(prefix, max_results)
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f'Error: {str(e)}')
        return jsonify({'error': str(e)}), 500