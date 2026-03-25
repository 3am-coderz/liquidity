@echo off
cd /d C:\Users\Kathir\Downloads\project\backend
C:\Users\Kathir\Downloads\project\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 1> C:\Users\Kathir\Downloads\project\.logs\backend.out.log 2> C:\Users\Kathir\Downloads\project\.logs\backend.err.log
