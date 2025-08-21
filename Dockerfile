# PCBA Test System - Docker Image
FROM python:3.11-slim

# Sistem paketlerini güncelle ve gerekli araçları yükle
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini oluştur
WORKDIR /app

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY app.py .
COPY dash/ dash/

# SQLite veritabanı için volume mount noktası
VOLUME ["/app/data"]

# Port 9002'i aç
EXPOSE 9002

# Veritabanı dosyasının data dizininde olması için environment variable
ENV DATABASE_PATH=/app/data/pcba_test.db
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=9002

# Uygulamayı başlat
CMD ["python", "app.py"]