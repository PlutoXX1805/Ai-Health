@echo off
cd /d "%~dp0"
where py >nul 2>&1 && py generate_design_doc.py && exit /b %ERRORLEVEL%
where python >nul 2>&1 && python generate_design_doc.py && exit /b %ERRORLEVEL%
echo [ERROR] 未找到 Python。请安装 Python 3.10+，或在 PowerShell 中执行: py generate_design_doc.py
exit /b 1
