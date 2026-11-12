@echo off
REM Kullanim: calistir.bat baslangic.json komutlar.jsonl > sonuclar.jsonl
REM Once "py" (Windows Python baslaticisi) deneniyor, yoksa "python" komutu kullaniliyor.
REM %~dp0 bu .bat dosyasinin bulundugu klasor, %* verilen butun parametreler.
where py >nul 2>nul
if errorlevel 1 goto python_ile
py -3 "%~dp0komut_satiri.py" %*
exit /b %errorlevel%
:python_ile
python "%~dp0komut_satiri.py" %*
exit /b %errorlevel%
