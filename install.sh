#!/bin/bash
set -e
echo "Installing system dependencies..."
sudo apt-get update && sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pil

echo "Installing application files..."
sudo mkdir -p /usr/local/bin/character-card-generator
sudo cp card_model.py main.py /usr/local/bin/character-card-generator/

echo "Setting up desktop shortcut..."
sudo cp sillytavern-card-creator.desktop /usr/share/applications/
update-desktop-database

echo "Installation complete! You can now launch 'SillyTavern Card Creator' from your application menu."