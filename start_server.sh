#!/bin/bash

echo "PCBA Test Sistemi Başlatılıyor..."
echo "Port: 9002"
echo "URL: http://localhost:9002"

# Gerekli Python paketlerinin yüklü olup olmadığını kontrol et
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Hata: Flask yüklü değil. Lütfen requirements.txt dosyasındaki paketleri yükleyin."
    echo "Komut: pip install -r requirements.txt"
    exit 1
fi

# Veritabanı dosyasının var olup olmadığını kontrol et
if [ ! -f "instance/pcba_test_new.db" ]; then
    echo "Veritabanı bulunamadı. İlk kez çalıştırılıyor..."
    python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Veritabanı oluşturuldu.')"
fi

# Flask uygulamasını başlat
echo "Flask uygulaması başlatılıyor..."
python3 app.py