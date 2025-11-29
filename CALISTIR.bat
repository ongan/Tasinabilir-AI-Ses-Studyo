@echo off
title AI Ses Studyosu Baslatiliyor...
color 0A

:: Klasor yollarini ayarla
set "STUDIO_ROOT=%~dp0"

echo ========================================================
echo  TASINABILIR AI SES SERVISI BASLATILIYOR
echo  Lutfen pencereyi kapatmayin. 
echo  Islem bitince tarayici otomatik acilacak.
echo ========================================================
echo.

:: Lisans onayi
set "COQUI_TOS_AGREED=1"

:: Path ayarlari (Python ve FFmpeg)
set "PATH=%STUDIO_ROOT%Python310;%STUDIO_ROOT%Python310\Scripts;%STUDIO_ROOT%Tools\ffmpeg\bin;%PATH%"

:: Paneli baslat
python "%STUDIO_ROOT%Projects\panel.py"

pause