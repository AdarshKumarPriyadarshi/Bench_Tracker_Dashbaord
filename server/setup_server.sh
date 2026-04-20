#!/bin/bash
echo ""
echo " ============================================="
echo "  MBRDI Bench Tracker - Server Setup (Linux)"
echo " ============================================="
echo ""

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    echo " [!] Virtual environment already exists."
    echo "     Delete 'venv' folder to recreate."
    echo ""
    exit 0
fi

echo " [1/3] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo " [ERROR] Failed to create venv. Is Python3 installed?"
    exit 1
fi

echo " [2/3] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo " [3/3] Verifying..."
python3 -c "import fastapi, uvicorn, jinja2; print('       All packages OK')"

echo ""
echo " ============================================="
echo "  Setup Complete!"
echo " ============================================="
echo ""
echo "  Start server:  ./run_server.sh"
echo "  Dashboard:     http://$(hostname -I | awk '{print $1}'):8000"
echo ""
