#!/bin/bash
# Install script for Reviewer Service on macOS

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_NAME="com.reviewer.api"
PLIST_FILE="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"

echo "🚀 Installing Reviewer Service..."

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -e ."
    exit 1
fi

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ Error: GEMINI_API_KEY environment variable is not set."
    echo "   The service requires this to function."
    echo ""
    echo "   Please set it in one of these ways:"
    echo "   1. Export in your shell: export GEMINI_API_KEY='your-key-here'"
    echo "   2. Add to ~/.zshrc or ~/.bashrc"
    echo "   3. Create a .env file in the project directory"
    echo ""
    echo "   Then re-run this installer."
    exit 1
fi

# Create the plist file
echo "📝 Creating service configuration..."
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/venv/bin/python</string>
        <string>-m</string>
        <string>reviewer.service</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$SCRIPT_DIR</string>
        <key>REVIEWER_HOST</key>
        <string>127.0.0.1</string>
        <key>REVIEWER_PORT</key>
        <string>8765</string>
        <key>GEMINI_API_KEY</key>
        <string>$GEMINI_API_KEY</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/reviewer.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/reviewer.error.log</string>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

# Unload existing service if it exists
if launchctl list | grep -q "$SERVICE_NAME"; then
    echo "🔄 Stopping existing service..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
fi

# Load the new service
echo "🔧 Loading service..."
launchctl load "$PLIST_FILE"

# Start the service
echo "▶️  Starting service..."
launchctl start "$SERVICE_NAME"

# Wait a moment for service to start
sleep 2

# Check if service is running
if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "✅ Service installed and running successfully!"
    echo ""
    echo "📊 Service Status:"
    curl -s http://localhost:8765/health | python3 -m json.tool
    echo ""
    echo "🎯 Usage:"
    echo "   reviewer --session-name 'my-feature'    # Use persistent session"
    echo "   reviewer --list-sessions                # List active sessions"
    echo "   reviewer                                # Standard mode (no session)"
    echo ""
    echo "🛠  Management:"
    echo "   reviewer --service status   # Check status"
    echo "   reviewer --service logs     # View logs"
    echo "   reviewer --service restart  # Restart service"
else
    echo "❌ Service failed to start. Check logs:"
    echo "   tail -f /tmp/reviewer.error.log"
    exit 1
fi