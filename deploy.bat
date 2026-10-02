@echo off
setlocal
python -m pytest -q
if errorlevel 1 exit /b 1
python -m build
if errorlevel 1 exit /b 1
python -m twine check dist/*
if errorlevel 1 exit /b 1
echo Packages ready in dist. Tag and push explicitly to publish a GitHub release.
