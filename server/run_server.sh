#!/bin/bash
echo ""
echo " ============================================="
echo "  MBRDI Minerva Bench Tracker - Server"
echo " ============================================="

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo " [ERROR] Virtual environment not found. Run setup_server.sh first."
    exit 1
fi

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "  Dashboard:  http://localhost:8000"
echo "  Network:    http://${IP}:8000"
echo ""
echo "  Press Ctrl+C to stop."
echo " ============================================="
echo ""

source venv/bin/activate
cd app
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
