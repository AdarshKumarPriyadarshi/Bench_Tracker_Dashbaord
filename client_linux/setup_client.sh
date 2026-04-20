#!/bin/bash
echo ""
echo " ============================================="
echo "  MBRDI Bench Client - Linux Setup"
echo " ============================================="
echo ""

if [ "$EUID" -ne 0 ]; then
    echo " [ERROR] Please run as root: sudo ./setup_client.sh"
    exit 1
fi

read -p "  Enter Bench ID (1-5): " BENCH_ID
read -p "  Enter Server IP (e.g., 53.217.54.191): " SERVER_IP

INSTALL_DIR="/opt/bench-automation"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo " [1/6] Creating install directory..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/login_gate.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/session_monitor.py" "$INSTALL_DIR/"
if [ -f "$SCRIPT_DIR/MBRDI.png" ]; then
    cp "$SCRIPT_DIR/MBRDI.png" "$INSTALL_DIR/"
fi

echo " [2/6] Writing config..."
cat > "$INSTALL_DIR/config.ini" << EOF
[server]
url = http://${SERVER_IP}:8000
timeout = 10

[bench]
bench_id = ${BENCH_ID}
pc_type = linux
EOF
echo "        Bench $BENCH_ID -> Server $SERVER_IP"

echo " [3/6] Creating virtual environment (with system packages)..."
python3 -m venv --system-site-packages "$INSTALL_DIR/venv"

echo " [4/6] Verifying dependencies..."
if "$INSTALL_DIR/venv/bin/python" -c "import requests" 2>/dev/null; then
    echo "        requests library OK."
else
    echo "        [WARNING] requests not available system-wide."
    echo "        Install it: sudo apt install python3-requests -y"
    echo "        Or: pip3 install requests"
fi

if "$INSTALL_DIR/venv/bin/python" -c "import tkinter" 2>/dev/null; then
    echo "        tkinter OK."
else
    echo "        [WARNING] tkinter not available."
    echo "        Install it: sudo apt install python3-tk -y"
fi

echo " [5/6] Installing session monitor service..."
cat > /etc/systemd/system/bench-session-monitor.service << EOF
[Unit]
Description=Bench Usage Automation - Session Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/session_monitor.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bench-session-monitor.service
systemctl start bench-session-monitor.service

echo " [6/6] Adding login gate to autostart..."
# Create autostart desktop entry for all users
mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/bench-login-gate.desktop << EOF
[Desktop Entry]
Type=Application
Name=Bench Login Gate
Exec=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/login_gate.py
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

# Set permissions so non-root users can write logs
chmod 777 "$INSTALL_DIR"
touch "$INSTALL_DIR/login_gate.log" "$INSTALL_DIR/session_monitor.log"
chmod 666 "$INSTALL_DIR/login_gate.log" "$INSTALL_DIR/session_monitor.log"

echo ""
echo " ============================================="
echo "  Setup Complete!"
echo " ============================================="
echo ""
echo "  To test: $INSTALL_DIR/venv/bin/python $INSTALL_DIR/login_gate.py"
echo "  Status:  systemctl status bench-session-monitor"
echo ""
