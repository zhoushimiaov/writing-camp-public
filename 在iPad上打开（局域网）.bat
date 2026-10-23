@echo off
chcp 65001 >nul
title 写作小能手训练营 - iPad 局域网服务器
cd /d "%~dp0"
python server.py
pause
