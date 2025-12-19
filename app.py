from flask import Flask, jsonify
from .config import Config
from .controllers.upload_controller import upload_bp
import logging
import os

app = Flask(__name__)
app.config.from_object(Config)

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Registrar controller
app.register_blueprint(upload_bp, url_prefix='/api')

# Ruta raíz
@app.route('/')
def index():
    return jsonify({
        'service': 'GCS Chunk Upload Service',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'start_upload': 'POST /api/start-upload',
            'verify': 'POST /api/verify',
            'calculate_chunks': 'POST /api/calculate-chunks'
        }
    }), 200

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

# Error handler
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint no encontrado',
        'available_endpoints': [
            'GET /',
            'GET /health',
            'POST /api/start-upload',
            'POST /api/verify',
            'POST /api/calculate-chunks'
        ]
    }), 404

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f'Error: {str(error)}')
    return jsonify({'error': str(error)}), 500
