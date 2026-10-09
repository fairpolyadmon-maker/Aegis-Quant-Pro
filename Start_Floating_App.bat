@echo off
title Aegis Quant Pro Launcher
cd /d "%~dp0"

if exist "AegisQuantPro.exe" (
    start "" "AegisQuantPro.exe"
    exit
)

if exist "C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    start "" "C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "floating_masaniello.pyw"
    exit
)

pythonw floating_masaniello.pyw
