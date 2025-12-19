from google.cloud import storage
from flask import current_app
import uuid
import requests


class GCSService:
    """
    Servicio para subir archivos a GCS con división automática en chunks
    """
    
    def __init__(self):
        """
        Inicializa el servicio GCS
        """
        self.client = storage.Client()
        self.bucket_name = current_app.config['GCS_BUCKET_NAME']
        self.bucket = self.client.bucket(self.bucket_name)
        self.chunk_size = 5 * 1024 * 1024  # 5MB
        self.max_file_size = 1024 * 1024 * 1024  # 5GB
     
    def upload_in_chunks_auto(self, file, filename, content_type):
        """
        Sube archivo dividiéndolo automáticamente en chunks
        """
        # Generar nombre unico
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{filename}"
        
        # Obtener tamaño total del archivo
        file.seek(0, 2) 
        file_size = file.tell()
        file.seek(0)  # Volver al inicio
        
        current_app.logger.info("="*70)
        current_app.logger.info(f"INICIANDO UPLOAD CON CHUNKS AUTOMÁTICOS")
        current_app.logger.info(f"Archivo: {unique_filename}")
        current_app.logger.info(f"Tamaño total: {file_size:,} bytes ({file_size / (1024**2):.2f} MB)")
        current_app.logger.info(f"Tamaño de chunk: {self.chunk_size:,} bytes ({self.chunk_size / (1024**2):.2f} MB)")
        current_app.logger.info("="*70)
        
        # Crear blob en GCS usada para almacenar archivos
        blob = self.bucket.blob(unique_filename)
        
        # Iniciar sesión de carga reanudable
        # Esta URL es donde enviaremos los chunks
        session_url = blob.create_resumable_upload_session(
            content_type=content_type,
            size=file_size
        )
        
        current_app.logger.info(f" Sesión reanudable creada")
        current_app.logger.info(f"  Session URL: {session_url[:80]}...")
        
        # Calcular número total de chunks
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        current_app.logger.info(f" Total de chunks a enviar: {total_chunks}")
        
        # Variables para el loop
        uploaded_bytes = 0
        chunk_number = 1
        chunks_info = []
        
        # Loop principal: dividir y enviar chunks
        while uploaded_bytes < file_size:
            # Leer chunk del archivo
            chunk_data = file.read(self.chunk_size)
            chunk_length = len(chunk_data)
            
            # Calcular rango de bytes para este chunk
            start = uploaded_bytes
            end = uploaded_bytes + chunk_length - 1
            
            # Preparar headers requeridos por GCS
            headers = {
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Content-Length': str(chunk_length)
            }
            
            # Calcular progreso
            progress = (uploaded_bytes / file_size) * 100
            
            current_app.logger.info("")
            current_app.logger.info(f"Enviando chunk {chunk_number}/{total_chunks} ({progress:.1f}%)")
            current_app.logger.info(f"Bytes: {start:,} - {end:,} / {file_size:,}")
            current_app.logger.info(f"Tamaño: {chunk_length:,} bytes")
            current_app.logger.info(f"Content-Range: bytes {start}-{end}/{file_size}")
            
            try:
                # Enviar chunk a GCS usando PUT request
                response = requests.put(
                    session_url,
                    headers=headers,
                    data=chunk_data,
                    timeout=300  # 5 minutos de timeout
                )
                
                # Guardar información del chunk
                chunk_info = {
                    'chunk_number': chunk_number,
                    'start': start,
                    'end': end,
                    'size': chunk_length,
                    'status_code': response.status_code,
                    'progress_percentage': round(progress, 2)
                }
                chunks_info.append(chunk_info)
                
                # Analizar respuesta de GCS
                if response.status_code == 308:
                    # 308 Resume Incomplete - GCS recibió el chunk, espera más
                    current_app.logger.info(f"Respuesta: 308 Resume Incomplete")
                    current_app.logger.info(f"Chunk {chunk_number} recibido correctamente")
                    current_app.logger.info(f"Continuando con siguiente chunk")
                    
                    uploaded_bytes = end + 1
                    chunk_number += 1
                    
                elif response.status_code in [200, 201]:
                    # 200/201 OK - Upload completado!
                    current_app.logger.info(f"Respuesta: {response.status_code} OK")
                    current_app.logger.info(f"Chunk {chunk_number} recibido correctamente")
                    current_app.logger.info("")
                    current_app.logger.info("="*70)
                    current_app.logger.info(f"UPLOAD COMPLETADO EXITOSAMENTE")
                    current_app.logger.info(f"Archivo: {unique_filename}")
                    current_app.logger.info(f"Total de chunks enviados: {chunk_number}")
                    current_app.logger.info("="*70)
                    
                    # Recargar blob para obtener metadata actualizada
                    blob.reload()
                    
                    # Retornar información completa del upload
                    return {
                        'success': True,
                        'unique_filename': unique_filename,
                        'original_filename': filename,
                        'size': blob.size,
                        'size_mb': round(blob.size / (1024 * 1024), 2),
                        'size_gb': round(blob.size / (1024 * 1024 * 1024), 2),
                        'content_type': blob.content_type,
                        'md5_hash': blob.md5_hash,
                        'created': blob.time_created.isoformat() if blob.time_created else None,
                        'public_url': f'gs://{self.bucket_name}/{unique_filename}',
                        'method': 'chunked_upload_auto',
                        'chunks': {
                            'total': chunk_number,
                            'chunk_size': self.chunk_size,
                            'chunk_size_mb': round(self.chunk_size / (1024 * 1024), 2),
                            'details': chunks_info
                        },
                        'message': f'Archivo subido exitosamente en {chunk_number} chunks'
                    }
                    
                else:
                    # Error inesperado
                    error_msg = f"Error HTTP {response.status_code} al subir chunk {chunk_number}"
                    current_app.logger.error("")
                    current_app.logger.error("="*70)
                    current_app.logger.error(f" {error_msg}")
                    current_app.logger.error(f"   Response body: {response.text}")
                    current_app.logger.error("="*70)
                    
                    raise Exception(f"{error_msg}: {response.text}")
                    
            except requests.exceptions.Timeout:
                error_msg = f"Timeout al enviar chunk {chunk_number}"
                current_app.logger.error(f" {error_msg}")
                raise Exception(error_msg)
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Error de red al enviar chunk {chunk_number}: {str(e)}"
                current_app.logger.error(f" {error_msg}")
                raise Exception(error_msg)
        
        # Si llegamos aquí, algo salió mal (loop terminó sin recibir 200)
        error_msg = "archivo incompleto: Se enviaron todos los chunks pero no se recibió confirmación"
        current_app.logger.error(f" {error_msg}")
        raise Exception(error_msg)
    
    def upload_file_directly(self, file):
        """
        Sube archivo completo de una vez (sin chunks)
        Método simple para archivos pequeños
        
        Args:
            file: FileStorage object de Flask
        
        Returns:
            dict con información del archivo subido
        """
        # Generar nombre único
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{file.filename}"
        
        # Crear blob
        blob = self.bucket.blob(unique_filename)
        
        # Determinar content type
        content_type = file.content_type or 'application/octet-stream'
        
        current_app.logger.info(f"Iniciando upload directo: {unique_filename}")
        
        # Subir archivo completo de una vez
        blob.upload_from_file(
            file,
            content_type=content_type,
            rewind=True  # Asegura que empiece desde el inicio del archivo
        )
        
        # Recargar para obtener metadata
        blob.reload()
        
        current_app.logger.info(f" Upload completado: {unique_filename} ({blob.size} bytes)")
        
        return {
            'success': True,
            'unique_filename': unique_filename,
            'original_filename': file.filename,
            'size': blob.size,
            'size_mb': round(blob.size / (1024 * 1024), 2),
            'content_type': blob.content_type,
            'created': blob.time_created.isoformat() if blob.time_created else None,
            'md5_hash': blob.md5_hash,
            'public_url': f'gs://{self.bucket_name}/{unique_filename}',
            'message': 'Archivo subido exitosamente',
            'method': 'direct_upload'
        }
    
    def verify_file(self, filename):
        """
        Verifica si un archivo existe en GCS y obtiene su información
        """
        blob = self.bucket.blob(filename)
        
        # Verificar existencia
        if not blob.exists():
            current_app.logger.warning(f"Archivo no encontrado: {filename}")
            return {
                'success': False,
                'exists': False,
                'filename': filename,
                'message': 'El archivo no existe en GCS'
            }
        
        # Recargar metadata
        blob.reload()
        
        current_app.logger.info(f" Archivo verificado: {filename}")
        
        return {
            'success': True,
            'exists': True,
            'filename': filename,
            'size': blob.size,
            'size_mb': round(blob.size / (1024 * 1024), 2),
            'size_gb': round(blob.size / (1024 * 1024 * 1024), 2),
            'content_type': blob.content_type,
            'created': blob.time_created.isoformat() if blob.time_created else None,
            'updated': blob.updated.isoformat() if blob.updated else None,
            'md5_hash': blob.md5_hash,
            'public_url': f'gs://{self.bucket_name}/{filename}',
            'generation': blob.generation
        }
    
    def list_files(self, prefix='', max_results=20):
        """
        Lista archivos en el bucket
        
        Args:
            prefix: Prefijo para filtrar archivos (opcional)
            max_results: Máximo número de resultados (default: 20)
        
        Returns:
            dict con lista de archivos y estadísticas
        """
        current_app.logger.info(f"Listando archivos (prefix='{prefix}', max={max_results})")
        
        # Obtener blobs del bucket
        blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_results)
        
        files = []
        total_size = 0
        
        # Iterar sobre cada blob
        for blob in blobs:
            file_info = {
                'filename': blob.name,
                'size': blob.size,
                'size_mb': round(blob.size / (1024 * 1024), 2),
                'content_type': blob.content_type,
                'created': blob.time_created.isoformat() if blob.time_created else None,
                'md5_hash': blob.md5_hash
            }
            files.append(file_info)
            total_size += blob.size
        
        current_app.logger.info(f" Encontrados {len(files)} archivos")
        
        return {
            'success': True,
            'bucket': self.bucket_name,
            'count': len(files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'files': files
        }
