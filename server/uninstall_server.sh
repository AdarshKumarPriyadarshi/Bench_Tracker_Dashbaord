#!/bin/bash
echo ""
echo " ============================================="
echo "  MBRDI Bench Tracker - Uninstall Server"
echo " ============================================="
echo ""

cd "$(dirname "$0")"

read -p "  Remove server from this PC? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo " Cancelled."
    exit 0
fi

echo ""
echo " [1/3] Stopping server..."
pkill -f "uvicorn main:app" 2>/dev/null
echo "        Done."

echo " [2/3] Deleting virtual environment..."
rm -rf venv
echo "        Done."

echo " [3/3] Cleaning database and logs..."
rm -f app/bench_data.db
rm -f app/server.log
echo "        Done."

echo ""
echo " ============================================="
echo "  Uninstall Complete!"
echo " ============================================="
echo ""
echo "  To reinstall: ./setup_server.sh"
echo ""
