def calculate_chunk_ranges(file_size, chunk_size):
    """
    Calcula los rangos de bytes para cada chunk
   
    """
    chunks = []
    start = 0
    chunk_number = 1
    
    while start < file_size:
        # Calcular ultimo byte del chunk, índice empieza en 0
        end = min(start + chunk_size - 1, file_size - 1)
        
        # Tamaño del chunk
        current_chunk_size = end - start + 1
        
        chunks.append({
            'chunk_number': chunk_number,
            'start': start,
            'end': end,
            'size': current_chunk_size,
            'size_mb': round(current_chunk_size / (1024**2), 2),
            'content_range': f'bytes {start}-{end}/{file_size}',
            'content_length': current_chunk_size,
            'is_last': (end == file_size - 1),
            'instructions': f'PUT session_url con headers: Content-Range: bytes {start}-{end}/{file_size}, Content-Length: {current_chunk_size}'
        })
        
        start = end + 1
        chunk_number += 1
    
    return chunks


def format_bytes(bytes_size):
    """
    Formatea bytes a formato legible
    
    """
    if bytes_size == 0:
        return '0 B'
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.2f} EB"