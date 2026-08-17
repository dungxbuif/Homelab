#!/bin/bash

# Ktunnel Binary Installation Script
# Downloads and installs ktunnel binary locally

set -e

KTUNNEL_VERSION="v1.6.1"
KTUNNEL_ARCH="Linux_x86_64"
KTUNNEL_URL="https://github.com/omrikiei/ktunnel/releases/download/${KTUNNEL_VERSION}/ktunnel_${KTUNNEL_VERSION#v}_${KTUNNEL_ARCH}.tar.gz"

echo "📥 Installing ktunnel ${KTUNNEL_VERSION}..."
echo "========================================"

# Check if ktunnel is already installed
if command -v ktunnel &> /dev/null; then
    CURRENT_VERSION=$(ktunnel version 2>/dev/null | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
    echo "ℹ️  ktunnel is already installed (version: ${CURRENT_VERSION})"
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Keeping existing installation"
        exit 0
    fi
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo "📦 Downloading ktunnel ${KTUNNEL_VERSION}..."
wget -q --show-progress "$KTUNNEL_URL" -O ktunnel.tar.gz

echo "📁 Extracting archive..."
tar -xzf ktunnel.tar.gz

echo "🔧 Installing to /usr/local/bin..."
sudo mv ktunnel /usr/local/bin/
sudo chmod +x /usr/local/bin/ktunnel

# Verify installation
echo "✅ Verifying installation..."
if command -v ktunnel &> /dev/null; then
    INSTALLED_VERSION=$(ktunnel version 2>/dev/null | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
    echo "🎉 ktunnel ${INSTALLED_VERSION} installed successfully!"
else
    echo "❌ Installation failed"
    exit 1
fi

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "📝 Usage:"
echo "========="
echo "ktunnel expose <service-name> <local-port>:<remote-port> -n <namespace>"
echo ""
echo "📖 For more information: ktunnel --help"
