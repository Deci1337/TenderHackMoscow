@echo off
cd /d "c:\Users\HONOR\Desktop\TenderHackMoscow\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
