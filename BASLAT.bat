@echo off
title AI STUDIO - GELISTIRICI MODU
color 0E

echo ==================================================
echo  VS CODE PORTABLE ORTAMINDA ACILIYOR...
echo ==================================================

:: Yollari Tanimla
set "STUDIO_ROOT=%~dp0"
set "PATH=%STUDIO_ROOT%Python310;%STUDIO_ROOT%Python310\Scripts;%STUDIO_ROOT%Tools\ffmpeg\bin;%PATH%"

:: VS Code'u Ac (Projects klasoruyle birlikte)
start "" "%STUDIO_ROOT%VSCode\Code.exe" "%STUDIO_ROOT%Projects"

exit