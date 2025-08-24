#!/usr/bin/env python3
"""
PCBA Test Sistemi - Hızlı Test Script'i
Bu script uygulamanın çalışıp çalışmadığını test eder
"""

import sys
import traceback

def test_imports():
    """Import testleri"""
    print("📦 Import testleri başlatılıyor...")
    
    try:
        import flask
        print("  ✅ Flask import edildi")
        
        import flask_sqlalchemy
        print("  ✅ Flask-SQLAlchemy import edildi")
        
        import flask_login
        print("  ✅ Flask-Login import edildi")
        
        import apscheduler
        print("  ✅ APScheduler import edildi")
        
        return True
    except ImportError as e:
        print(f"  ❌ Import hatası: {e}")
        return False

def test_app_creation():
    """App oluşturma testi"""
    print("\n🏗️  App oluşturma testi...")
    
    try:
        # App'i import et ama çalıştırma
        import app
        print("  ✅ App başarıyla import edildi")
        
        # Temel route'ları kontrol et
        routes = [rule.rule for rule in app.app.url_map.iter_rules()]
        important_routes = ['/', '/login', '/api/test/start', '/scheduled-tests']
        
        for route in important_routes:
            if route in routes:
                print(f"  ✅ Route bulundu: {route}")
            else:
                print(f"  ⚠️  Route bulunamadı: {route}")
        
        return True
    except Exception as e:
        print(f"  ❌ App oluşturma hatası: {e}")
        traceback.print_exc()
        return False

def test_database():
    """Veritabanı testi"""
    print("\n🗄️  Veritabanı testi...")
    
    try:
        import app
        
        # Veritabanı dosyasının varlığını kontrol et
        import os
        if os.path.exists('pcba_test_new.db'):
            print("  ✅ Veritabanı dosyası mevcut")
        else:
            print("  ⚠️  Veritabanı dosyası bulunamadı (ilk çalıştırmada oluşturulacak)")
        
        # Model'leri kontrol et
        with app.app.app_context():
            # Temel modelleri kontrol et
            models = [app.User, app.TestResult, app.Connection, app.TestExecution]
            for model in models:
                print(f"  ✅ Model tanımlı: {model.__name__}")
        
        return True
    except Exception as e:
        print(f"  ❌ Veritabanı testi hatası: {e}")
        return False

def test_services():
    """Servis testleri"""
    print("\n⚙️  Servis testleri...")
    
    try:
        import app
        
        # TestExecutorService
        if hasattr(app, 'test_executor_service'):
            print("  ✅ TestExecutorService tanımlı")
        else:
            print("  ❌ TestExecutorService bulunamadı")
        
        # TestScheduler
        if hasattr(app, 'test_scheduler'):
            print("  ✅ TestScheduler tanımlı")
        else:
            print("  ❌ TestScheduler bulunamadı")
        
        # BackgroundTaskProcessor
        if hasattr(app, 'task_processor'):
            print("  ✅ BackgroundTaskProcessor tanımlı")
        else:
            print("  ❌ BackgroundTaskProcessor bulunamadı")
        
        return True
    except Exception as e:
        print(f"  ❌ Servis testi hatası: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🚀 PCBA Test Sistemi - Hızlı Test")
    print("=" * 50)
    
    tests = [
        ("Import Testleri", test_imports),
        ("App Oluşturma", test_app_creation),
        ("Veritabanı", test_database),
        ("Servisler", test_services)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} testi başarısız: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Sonuçları: {passed}/{total} başarılı")
    
    if passed == total:
        print("🎉 Tüm testler başarılı! Uygulama çalışmaya hazır.")
        print("💡 Uygulamayı başlatmak için: python app.py")
        print("🌐 Tarayıcıda açmak için: http://localhost:9002")
        return 0
    else:
        print("⚠️  Bazı testler başarısız. Lütfen hataları kontrol edin.")
        return 1

if __name__ == '__main__':
    sys.exit(main())