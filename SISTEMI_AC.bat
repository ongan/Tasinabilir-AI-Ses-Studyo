@echo off
title AI STUDIO ANA KUMANDA (V25.0)
color 0A

:: --- 1. YOL TANIMLAMALARI (Hayati Kısım) ---
set "STUDIO_ROOT=%~dp0"
:: Python ve FFmpeg'i sisteme tanitiyoruz
set "PATH=%STUDIO_ROOT%Python310;%STUDIO_ROOT%Python310\Scripts;%STUDIO_ROOT%Tools\ffmpeg\bin;%PATH%"

echo ==========================================================
echo  YAPAY ZEKA MEDYA FABRIKASI BASLATILIYOR
echo ==========================================================
echo.

:: --- 2. OLLAMA (BEYİN) BASLATMA ---
echo [1/3] Ollama Sunucusu Aciliyor...
:: Yeni bir pencerede acar, kapanmasini engeller
start "OLLAMA SERVER" cmd /k "%STUDIO_ROOT%Tools\Ollama\OLLAMA_BASLAT.bat"

:: Ollama'nin kendine gelmesi icin 5 saniye bekle
timeout /t 5 >nul

:: --- 3. MOTOR (WORKER) BASLATMA ---
echo.
echo [2/3] Uretim Motoru (Worker) Aciliyor...
:: Hata alsa bile kapanmamasi icin 'cmd /k' kullaniyoruz
start "AI MOTORU (KAPATMA!)" cmd /k python "%STUDIO_ROOT%Projects\worker.py"

:: --- 4. ARAYUZ (GUI) BASLATMA ---
echo.
echo [3/3] Arayuz (Web UI) Aciliyor...
python "%STUDIO_ROOT%Projects\arayuz.py"

pause