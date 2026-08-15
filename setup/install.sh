#!/bin/bash
# Setup script for personal-wiki on Orange Pi (Ubuntu/Debian)
# Run as root or with sudo

set -e

echo "=== personal-wiki setup ==="

# 1. System deps
apt-get update -qq
apt-get install -y -qq curl git

# 2. Node.js (if not installed)
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -qq nodejs
fi

echo "Node: $(node --version)"
echo "npm: $(npm --version)"

# 3. Install llmwiki-cli
npm install -g llmwiki-cli

# 4. Clone or pull repo
WIKI_DIR="$HOME/personal-wiki"
if [ -d "$WIKI_DIR/.git" ]; then
    echo "Pulling latest changes..."
    cd "$WIKI_DIR" && git pull
else
    echo "Cloning repo..."
    git clone https://github.com/ttenushko/personal-wiki.git "$WIKI_DIR"
    cd "$WIKI_DIR"
fi

# 5. Register wikis
wiki registry 2>/dev/null || true

# 6. Verify
wiki status --wiki "Личное"
wiki status --wiki "Разработка"
wiki status --wiki "Автомобили"

echo ""
echo "=== Done ==="
echo "Usage: cd $WIKI_DIR && wiki status"
echo "Or use --wiki flag: wiki --wiki 'Разработка' search 'query'"
