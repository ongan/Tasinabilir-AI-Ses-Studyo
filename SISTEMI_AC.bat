@echo off
title AI STUDIO ANA KUMANDA
set "STUDIO_ROOT=%~dp0"
set "PATH=%STUDIO_ROOT%Python310;%STUDIO_ROOT%Python310\Scripts;%STUDIO_ROOT%Tools\ffmpeg\bin;%PATH%"

echo ===================================================
echo  1. MOTOR BASLATILIYOR (KAPATMA KORUMALI)
echo ===================================================
:: Buradaki "cmd /k" pencerenin kapanmasini engeller
start "AI MOTORU" cmd /k python "%STUDIO_ROOT%Projects\worker.py"

echo.
echo ===================================================
echo  2. ARAYUZ BASLATILIYOR
echo ===================================================
python "%STUDIO_ROOT%Projects\arayuz.py"

pause