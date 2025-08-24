@echo off
echo PCBA Test Sistemi
echo ==========================================
echo 1. Hizli Test (test_app.py)
echo 2. Uygulamayi Baslat (app.py)
echo ==========================================
echo.
set /p choice="Seciminizi yapin (1 veya 2): "

if "%choice%"=="1" (
    echo.
    echo Hizli test baslatiliyor...
    python test_app.py
    echo.
    echo Test tamamlandi. Uygulamayi baslatmak ister misiniz? (y/n)
    set /p start_app=""
    if /i "%start_app%"=="y" (
        goto start_app
    ) else (
        pause
        exit /b 0
    )
)

if "%choice%"=="2" (
    goto start_app
)

echo Gecersiz secim!
pause
exit /b 1

:start_app
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