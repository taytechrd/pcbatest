# Haberleşme Log Sistemi - Tasarım Dökümanı

## Genel Bakış

Haberleşme Log Sistemi, PCBA Test Sistemi'nin test cihazlarıyla olan tüm haberleşmelerini kayıt altına alan, izleyen ve yöneten kapsamlı bir modüldür. Sistem hem seri port hem de TCP bağlantılarını destekler ve gerçek zamanlı monitoring sağlar.

## Mimari

### Sistem Bileşenleri

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface                            │
├─────────────────────────────────────────────────────────────┤
│  Communication Log Page  │  Connection Status  │  Settings  │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Flask Backend                            │
├─────────────────────────────────────────────────────────────┤
│  Log API  │  Connection Manager  │  WebSocket Handler       │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                Communication Layer                          │
├─────────────────────────────────────────────────────────────┤
│  Serial Handler  │  TCP Handler  │  Protocol Parser        │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Database                                 │
├─────────────────────────────────────────────────────────────┤
│  Communication Logs  │  Connection Configs  │  Statistics  │
└─────────────────────────────────────────────────────────────┘
```

## Veri Modelleri

### CommunicationLog Model
```python
class CommunicationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection_config.id'))
    direction = db.Column(db.String(10))  # 'sent', 'received'
    data_hex = db.Column(db.Text)
    data_ascii = db.Column(db.Text)
    data_size = db.Column(db.Integer)
    is_error = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.String(500))
    response_time = db.Column(db.Float)  # milliseconds
```

### ConnectionConfig Model
```python
class ConnectionConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    connection_type = db.Column(db.String(20))  # 'serial', 'tcp'
    is_active = db.Column(db.Boolean, default=True)
    
    # Serial Port Settings
    port = db.Column(db.String(50))
    baud_rate = db.Column(db.Integer, default=9600)
    data_bits = db.Column(db.Integer, default=8)
    stop_bits = db.Column(db.Integer, default=1)
    parity = db.Column(db.String(10), default='none')
    
    # TCP Settings
    ip_address = db.Column(db.String(15))
    tcp_port = db.Column(db.Integer)
    timeout = db.Column(db.Integer, default=5000)
    
    # Status
    is_connected = db.Column(db.Boolean, default=False)
    last_connected = db.Column(db.DateTime)
    connection_duration = db.Column(db.Integer)  # seconds
```

### ConnectionStatistics Model
```python
class ConnectionStatistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection_config.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date())
    bytes_sent = db.Column(db.BigInteger, default=0)
    bytes_received = db.Column(db.BigInteger, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    messages_received = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    avg_response_time = db.Column(db.Float, default=0)
```

## Bileşen Tasarımı

### 1. Communication Manager
```python
class CommunicationManager:
    def __init__(self):
        self.connections = {}
        self.log_handlers = []
    
    def add_connection(self, config):
        """Yeni bağlantı ekle"""
        
    def remove_connection(self, connection_id):
        """Bağlantıyı kaldır"""
        
    def send_data(self, connection_id, data):
        """Data gönder ve logla"""
        
    def get_connection_status(self, connection_id):
        """Bağlantı durumunu getir"""
```

### 2. Serial Communication Handler
```python
class SerialHandler:
    def __init__(self, config):
        self.config = config
        self.serial_connection = None
        
    def connect(self):
        """Seri port bağlantısı kur"""
        
    def disconnect(self):
        """Bağlantıyı kapat"""
        
    def send_command(self, command):
        """Komut gönder ve cevap bekle"""
        
    def read_response(self):
        """Cevap oku"""
```

### 3. TCP Communication Handler
```python
class TCPHandler:
    def __init__(self, config):
        self.config = config
        self.socket = None
        
    def connect(self):
        """TCP bağlantısı kur"""
        
    def disconnect(self):
        """Bağlantıyı kapat"""
        
    def send_data(self, data):
        """Data gönder"""
        
    def receive_data(self):
        """Data al"""
```

## Kullanıcı Arayüzü Tasarımı

### 1. Communication Log Sayfası
- **Real-time Log Table**: Gerçek zamanlı log tablosu
- **Filter Panel**: Tarih, bağlantı tipi, hata durumu filtreleri
- **Connection Status Cards**: Bağlantı durumu kartları
- **Manual Command Panel**: Manuel komut gönderme paneli

### 2. Connection Management Sayfası
- **Connection List**: Yapılandırılmış bağlantılar listesi
- **Add/Edit Connection**: Bağlantı ekleme/düzenleme formu
- **Test Connection**: Bağlantı test butonu
- **Statistics Dashboard**: İstatistik dashboard'u

### 3. Log Analysis Sayfası
- **Search Interface**: Gelişmiş arama arayüzü
- **Export Options**: Dışa aktarma seçenekleri
- **Charts and Graphs**: Grafik ve istatistikler
- **Archive Management**: Arşiv yönetimi

## API Tasarımı

### REST Endpoints
```
GET    /api/communication/logs              # Log listesi
POST   /api/communication/logs/search       # Log arama
GET    /api/communication/connections       # Bağlantı listesi
POST   /api/communication/connections       # Yeni bağlantı
PUT    /api/communication/connections/:id   # Bağlantı güncelle
DELETE /api/communication/connections/:id   # Bağlantı sil
POST   /api/communication/test/:id          # Bağlantı test
POST   /api/communication/send/:id          # Manuel data gönder
GET    /api/communication/statistics        # İstatistikler
POST   /api/communication/export            # Log export
```

### WebSocket Events
```
connection_status_changed    # Bağlantı durumu değişti
new_log_entry               # Yeni log kaydı
error_occurred              # Hata oluştu
statistics_updated          # İstatistikler güncellendi
```

## Güvenlik Considerations

### 1. Erişim Kontrolü
- Sadece yetkili kullanıcılar haberleşme loglarını görüntüleyebilir
- Manuel komut gönderme sadece admin yetkisi gerektirir
- Bağlantı yapılandırması admin yetkisi gerektirir

### 2. Data Güvenliği
- Hassas veriler şifrelenerek saklanır
- Log dosyaları güvenli dizinde tutulur
- Export işlemleri audit loglanır

### 3. Rate Limiting
- API çağrıları rate limit'e tabidir
- Manuel komut gönderme sınırlandırılır
- WebSocket bağlantıları kontrol edilir

## Performans Optimizasyonları

### 1. Database Optimizations
- Log tablosu için partitioning
- Index optimizasyonları
- Otomatik arşivleme

### 2. Real-time Updates
- WebSocket kullanımı
- Efficient data serialization
- Client-side caching

### 3. Memory Management
- Connection pooling
- Buffer management
- Garbage collection optimization

## Hata Yönetimi

### 1. Connection Errors
- Automatic retry mechanisms
- Graceful degradation
- Error notification system

### 2. Data Corruption
- Checksum validation
- Data integrity checks
- Recovery procedures

### 3. System Errors
- Exception handling
- Logging and monitoring
- Alerting system

## Test Stratejisi

### 1. Unit Tests
- Communication handlers
- Data models
- API endpoints

### 2. Integration Tests
- End-to-end communication flow
- Database operations
- WebSocket functionality

### 3. Performance Tests
- Load testing
- Stress testing
- Memory leak detection

## Deployment Considerations

### 1. Dependencies
- pyserial for serial communication
- socket library for TCP
- Flask-SocketIO for WebSocket
- Additional monitoring tools

### 2. Configuration
- Environment-specific settings
- Connection configurations
- Logging levels

### 3. Monitoring
- System health checks
- Performance metrics
- Error tracking