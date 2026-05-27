# Imagen base ligera de Python 3.11
FROM python:3.11-slim

# Evita buffers y mejora logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Asegura que Python encuentre los módulos
ENV PYTHONPATH=/app

# Instalar dependencias del sistema (opcional pero recomendado)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . /app

# (Opcional) Log para verificar contenido
RUN echo "Contenido de /app:" && ls -l /app

# Cloud Run expone el puerto por variable PORT
EXPOSE 8080

# Ejecutar con Gunicorn 
CMD ["sh", "-c", "gunicorn app:app -b 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 180 --graceful-timeout 30 --keep-alive 5"]
