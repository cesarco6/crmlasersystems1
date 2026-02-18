# Usamos una imagen ligera de Python 3.12 basada en Debian Bookworm
FROM python:3.12-slim-bookworm

# Variables de entorno para optimizar Python en contenedores
# Evita que Python genere archivos .pyc innecesarios
ENV PYTHONDONTWRITEBYTECODE 1
# Envía los logs directamente a la terminal sin retrasos
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema para PostgreSQL y herramientas de red [cite: 4]
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos las dependencias de Python primero (para caché de Docker)
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del CRM al contenedor
COPY . /app/

# Comando por defecto para iniciar (será sobrescrito por docker-compose en desarrollo)
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]