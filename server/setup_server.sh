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
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY ALL_PROXY all_proxy SOCKS_PROXY socks_proxy
pip config set global.proxy "" --quiet 2>/dev/null
pip install pysocks --quiet --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install --upgrade pip --quiet --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org
pip install -r requirements.txt --quiet --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org

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
