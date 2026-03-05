#!/bin/bash
# FinanceChat — local dev server
# Usage: chmod +x start.sh && ./start.sh

set -e
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  💹 FinanceChat — Local Dev Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📦 Checking dependencies..."
/usr/bin/pip3 install flask flask-cors pdfplumber anthropic werkzeug --quiet --break-system-packages 2>/dev/null || \
  pip3 install flask flask-cors pdfplumber anthropic werkzeug --quiet

echo "✅ Dependencies ready"
echo "🚀 Starting on http://localhost:5050"
echo "   Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

/usr/bin/python3 api/index.py
