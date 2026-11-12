@echo off
REM Masaustu uygulamasini baslatir. Siyah konsol penceresi acilmasin diye pyw / pythonw kullaniliyor.
REM Istenirse baslangic dosyasi parametre olarak verilebilir: masaustu_uygulamasi.bat ornek\baslangic.json
where pyw >nul 2>nul
if errorlevel 1 goto pythonw_ile
start "" pyw -3 "%~dp0masaustu_uygulamasi.py" %*
exit /b 0
:pythonw_ile
where pythonw >nul 2>nul
if errorlevel 1 goto python_ile
start "" pythonw "%~dp0masaustu_uygulamasi.py" %*
exit /b 0
:python_ile
python "%~dp0masaustu_uygulamasi.py" %*
