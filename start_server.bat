@echo off
echo PCBA Test Sistemi Baslatiliyor...
echo ==========================================
echo.
echo Port: 9002
echo URL: http://localhost:9002

REM Gerekli Python paketlerinin yuklu olup olmadigini kontrol et
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Hata: Flask yuklu degil. Lutfen requirements.txt dosyasindaki paketleri yukleyin.
    echo Komut: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Veritabani dosyasinin var olup olmadigini kontrol et
if not exist "instance\pcba_test_new.db" (
    echo Veritabani bulunamadi. Ilk kez calistiriliyor...
    python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Veritabani olusturuldu.')"
)

REM Flask uygulamasini baslat
echo Flask uygulamasi baslatiliyor...
echo.
echo ==========================================
echo  PCBA Test Sistemi Hazir!
echo  URL: http://localhost:9002
echo  Kapatmak icin Ctrl+C basin
echo ==========================================
echo.

python app.py