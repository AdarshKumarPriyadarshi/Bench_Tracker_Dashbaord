#!/bin/bash
echo ""
echo " ============================================="
echo "  MBRDI Bench Client - Uninstall (Linux)"
echo " ============================================="
echo ""

if [ "$EUID" -ne 0 ]; then
    echo " [ERROR] Please run as root: sudo ./uninstall_client.sh"
    exit 1
fi

read -p "  Remove bench automation from this PC? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo " Cancelled."
    exit 0
fi

echo ""
echo " [1/4] Stopping services..."
systemctl stop bench-session-monitor.service 2>/dev/null
systemctl disable bench-session-monitor.service 2>/dev/null
rm -f /etc/systemd/system/bench-session-monitor.service
systemctl daemon-reload
echo "        Done."

echo " [2/4] Removing login gate from startup..."
rm -f /etc/xdg/autostart/bench-login-gate.desktop
sed -i '/bench-automation/d' /etc/xprofile 2>/dev/null
echo "        Done."

echo " [3/4] Deleting install directory..."
rm -rf /opt/bench-automation
echo "        Done."

echo " [4/4] Killing any running processes..."
pkill -f "login_gate.py" 2>/dev/null
pkill -f "session_monitor.py" 2>/dev/null
echo "        Done."

echo ""
echo " ============================================="
echo "  Uninstall Complete!"
echo " ============================================="
echo ""
echo "  To reinstall: run setup_client.sh"
echo ""
