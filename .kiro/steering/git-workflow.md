# Git Workflow Rules

## Git İşlemleri Kuralları

### Temel Kural
- Git işlemleri (add, commit, push, tag) **sadece kullanıcı açıkça istediğinde** yapılacak
- Otomatik git işlemleri yapılmayacak
- Kullanıcı "git yap", "commit et", "push et" gibi açık talimatlar verdiğinde işlem yapılacak

### İzin Verilen Durumlar
- Kullanıcı açıkça git komutu istediğinde
- Kullanıcı "değişiklikleri kaydet" dediğinde
- Kullanıcı "commit et" dediğinde
- Kullanıcı "push et" dediğinde

### Yasak Durumlar
- Kod değişikliği sonrası otomatik commit
- Dosya oluşturma/güncelleme sonrası otomatik add
- Herhangi bir işlem sonrası otomatik push
- Kullanıcı izni olmadan git tag oluşturma

### Özel Notlar
- Bu kural kalıcıdır ve tüm gelecek işlemlerde geçerlidir
- Sadece kullanıcının açık talebi üzerine git işlemleri yapılacak
- Kod tamamlandığında "git işlemi yapmak ister misin?" diye sormak yerine, sadece işlemin tamamlandığını belirt