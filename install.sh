#!/bin/bash
set -e

echo "🔧 Installing start_gui..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found."
    echo "   Install Python  3.6+ to continue."
    exit 1
fi

# Make executable
chmod +x start_gui.sh
echo "✅ Made start_gui.sh executable"

# Installation options
echo ""
echo "Installation Options:"
echo "  1. Install to PATH (/usr/local/bin/start_gui)"
echo "  2. Use in current directory (./start_gui.sh)"
echo ""
read -p "Choose [1/2]: " -n 1 -r
echo ""

if [[ $REPLY == "1" ]]; then
    if [ -w /usr/local/bin ]; then
        cp start_gui.sh /usr/local/bin/start_gui
        echo "✅ Installed to /usr/local/bin/start_gui"
        echo ""
        echo "🎉 Installation complete!"
        echo "   Try: start_gui --help"
    else
        echo "⚠️  Need sudo for /usr/local/bin"
        sudo cp start_gui.sh /usr/local/bin/start_gui
        echo "✅ Installed to /usr/local/bin/start_gui"
        echo ""
        echo "🎉 Installation complete!"
        echo "   Try: start_gui --help"
    fi
else
    echo "✅ Ready to use in current directory"
    echo ""
    echo "🎉 Installation complete!"
    echo "   Try: ./start_gui.sh --help"
fi
