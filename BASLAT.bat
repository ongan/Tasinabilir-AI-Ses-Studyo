@echo off
:: Burasi bizim tasinabilir stüdyomuzun ayarlarini yapar
echo AI STUDIO Baslatiliyor...
set "COQUI_TOS_AGREED=1"

:: Bulundugumuz klasoru alir
set "STUDIO_ROOT=%~dp0"

:: Python ve FFmpeg yollarini gecici olarak tanimlar (Sadece bu pencere icin)
set "PATH=%STUDIO_ROOT%Python310;%STUDIO_ROOT%Python310\Scripts;%STUDIO_ROOT%Tools\ffmpeg\bin;%PATH%"

:: VS Code'u bu ayarlarla acar
start "" "%STUDIO_ROOT%VSCode\Code.exe" "%STUDIO_ROOT%Projects"

exit