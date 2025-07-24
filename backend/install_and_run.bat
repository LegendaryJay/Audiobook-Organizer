@echo off
echo Installing Python dependencies...
pip install -r requirements.txt

echo Creating data directories...
if not exist "metadata" mkdir metadata
if not exist "covers" mkdir covers

echo Starting the Flask backend...
python app.py
pause
