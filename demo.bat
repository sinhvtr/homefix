@echo off
rem HomeFix - chay ban demo qua Cloudflare Quick Tunnel (xem docs\HUONG_DAN_DEMO.md).
rem Nhap dup de bat; hoac: demo.bat tat ^| demo.bat dev ^| demo.bat diachi
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo.ps1" %*
if "%~1"=="" pause
