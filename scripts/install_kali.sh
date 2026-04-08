#!/bin/bash
# ERR0RS ULTIMATE - Kali Linux Installation Script

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ERR0RS ULTIMATE - Installation for Kali Linux         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root (sudo ./install_kali.sh)"
    exit 1
fi

echo "📦 Installing system dependencies..."
apt update
apt install -y python3 python3-pip python3-venv git \
    postgresql redis nmap metasploit-framework \
    burpsuite hydra hashcat aircrack-ng \
    sqlmap nikto gobuster nuclei \
    python3-pyqt5 python3-pygame

echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🗄️  Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE errorz_ultimate;"
sudo -u postgres psql -c "CREATE USER errorz WITH PASSWORD 'changeme';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE errorz_ultimate TO errorz;"

echo ""
echo "⚙️  Configuring ERR0RS ULTIMATE..."
cp configs/example.env .env
echo "Please edit .env file with your API keys and configuration"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Activate venv: source venv/bin/activate"
echo "3. Run ERR0RS: python3 errorz.py"
echo ""
echo "🎉 Welcome to ERR0RS ULTIMATE!"
