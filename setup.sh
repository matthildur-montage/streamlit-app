#!/bin/bash

# Make script exit on first error
set -e

echo "Installing Playwright dependencies..."
apt-get update && apt-get install -y wget gnupg

# Install Playwright browsers with system dependencies
echo "Installing Playwright browsers..."
python -m playwright install --with-deps chromium

echo "Playwright setup completed successfully!"
