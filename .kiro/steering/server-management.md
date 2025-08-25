# Server Management Rules

## Flask Server Başlatma Kuralları

### Temel Kural
- `python app.py` komutu terminal'i bloke eder ve kullanıcı müdahalesini bekler
- Bu durumdan kaçınmak için **asla doğrudan `python app.py` kullanma**
- Her zaman background başlatma yöntemlerini kullan

### Önerilen Yöntemler

#### 1. Batch Dosyası Kullanma (En Önerilen)
```powershell
start start_server.bat
```
- ✅ Background'da çalışır
- ✅ Terminal'i bloke etmez
- ✅ Zaten mevcut dosya
- ✅ Kolay durdurulabilir

#### 2. PowerShell Background Process
```powershell
Start-Process python -ArgumentList "app.py" -WindowStyle Hidden
```
- ✅ Gizli pencerede çalışır
- ✅ Terminal'i bloke etmez

#### 3. PowerShell Job
```powershell
Start-Job -ScriptBlock { python app.py }
```
- ✅ Background job olarak çalışır
- ⚠️ Job yönetimi gerekir

### Server Durdurma

#### Tüm Python Processlerini Durdurma
```powershell
taskkill /f /im python.exe
```

#### Belirli Port'u Kullanan Process'i Durdurma
```powershell
netstat -ano | findstr :9002
taskkill /f /pid [PID_NUMBER]
```

### Yasak İşlemler
- ❌ Doğrudan `python app.py` kullanma
- ❌ Server başlatıp terminal'de bekleme
- ❌ Kullanıcı müdahalesini gerektiren komutlar

### Özel Notlar
- Server başlatıldıktan sonra test işlemlerine devam et
- Server loglarını kontrol etmek gerekirse ayrı terminal kullan
- Bu kural kalıcıdır ve tüm gelecek işlemlerde geçerlidir