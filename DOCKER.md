# Docker Deployment Guide - PCBA Test System

## Hızlı Başlangıç

### 1. Docker Container Oluşturma ve Çalıştırma

```bash
# Önce data dizini oluşturun
mkdir data

# Windows için
docker-compose -f docker-compose.windows.yml up -d

# Linux için  
docker-compose up -d
```

### 2. Web Arayüzüne Erişim

- **URL:** http://localhost:9001
- **Kullanıcı:** admin
- **Şifre:** admin123

## Serial Port ve TCP Port Desteği

### ✅ TCP Portları (Sorunsuz)
- **Modbus TCP:** Port 502 otomatik olarak yönlendirilir
- **Web Arayüzü:** Port 9001 host'a açılır
- Herhangi bir ek yapılandırma gerektirmez

### ⚠️ Serial Portları (Dikkat Gerekli)

#### **Linux Sistemlerde:**
```bash
# USB-Serial dönüştürücü
docker run --device=/dev/ttyUSB0 ...

# Yerleşik COM portları
docker run --device=/dev/ttyS0 --device=/dev/ttyS1 ...

# Tüm serial portlara erişim (kolay ama güvenlik riski)
docker run --privileged -v /dev:/dev ...
```

#### **Windows Sistemlerde:**
Windows'da serial port Docker desteği sınırlıdır. Önerilen çözümler:

**Yöntem 1: TCP-Serial Bridge**
```bash
# Host'da ser2net veya benzeri bir araç çalıştırın
# COM1 -> TCP:4001, COM2 -> TCP:4002
ser2net -c ser2net.conf

# Docker container'da TCP bağlantısı kullanın
# COM1 yerine host:4001 kullanın
```

**Yöntem 2: Host Network Mode**
```yaml
services:
  pcba-test:
    network_mode: host
    # Bu durumda tüm host portlarına erişim olur
```

## Veri Kalıcılığı

### Veritabanı
- SQLite veritabanı `./data/` dizininde saklanır
- Container silinse bile veriler korunur

### Yedekleme
```bash
# Veritabanını yedekleme
docker cp pcba-test-system:/app/data/pcba_test.db ./backup/

# Yedekten geri yükleme
docker cp ./backup/pcba_test.db pcba-test-system:/app/data/
```

## Production Deployment

### Environment Variables
```yaml
environment:
  - FLASK_ENV=production
  - DATABASE_PATH=/app/data/pcba_test.db
  - SECRET_KEY=your_secret_key_here
```

### Nginx Reverse Proxy (İsteğe Bağlı)
```nginx
server {
    listen 80;
    server_name pcba-test.local;
    
    location / {
        proxy_pass http://pcba-test:9001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Sorun Giderme

### Container Loglarını Görme
```bash
docker-compose logs -f pcba-test
```

### Container'a Shell Erişimi
```bash
docker exec -it pcba-test-system /bin/bash
```

### Serial Port Kontrolü (Linux)
```bash
# Host sistemde
ls -la /dev/tty* | grep -E "(USB|S[0-9])"

# Container içinde
docker exec pcba-test-system ls -la /dev/tty*
```

### Port Çakışması
```bash
# Port kullanımını kontrol etme
netstat -tulpn | grep :9001

# Farklı port kullanma
docker-compose up -d -e HOST_PORT=9002
```

## Güvenlik Notları

⚠️ **Önemli:** `privileged: true` ve `/dev` mount'u güvenlik riski oluşturabilir

**Üretim için önerilen güvenlik:**
1. Sadece gerekli serial portları mount edin
2. `privileged: true` yerine specific capabilities kullanın
3. Firewall kuralları ekleyin
4. SSL/TLS sertifikası kullanın

## Docker Commands Cheat Sheet

```bash
# Container'ı başlatma
docker-compose up -d

# Container'ı durdurma  
docker-compose down

# Logları görme
docker-compose logs -f

# Container'ı yeniden başlatma
docker-compose restart

# Image'ı yeniden build etme
docker-compose build --no-cache

# Tüm verileri temizleme
docker-compose down -v
rm -rf ./data/*
```