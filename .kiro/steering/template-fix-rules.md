# Template Fix Rules

## Değişken Değiştirme Kuralları

### Temel Kural
- Template dosyalarında değişken adı değiştirirken **tüm referansları** değiştir
- Sadece kritik olanları değiştirip diğerlerini unutma
- Eksik değişiklik template hatalarına neden olur

### Zorunlu İşlemler
- Değişken adı değiştirildiğinde dosyadaki **TÜM** referansları bul
- **HİÇBİRİNİ** atlama
- Değiştirme işlemini **TAMAMEN** bitir

### Örnek Durum
- Route'dan `scenario` gönderiliyorsa template'de `test_scenario` kullanılamaz
- Template'deki **TÜM** `test_scenario` referansları `scenario` olmalı
- Yarım bırakılan işlemler 500 hatalarına neden olur

### Özel Notlar
- Bu kural kalıcıdır ve tüm template düzenleme işlemlerinde geçerlidir
- Değişken değiştirme işlemi başlatıldığında sonuna kadar devam edilmeli
- Eksik değişiklikler sistem hatalarına neden olur