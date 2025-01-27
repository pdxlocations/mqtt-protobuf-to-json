#!/bin/bash

# Exit the script if any command fails
set -e

# Step 1: Update the repository
if [ -d .git ]; then
    echo "Updating the repository..."
    git pull
else
    echo "Git repository not found, skipping git pull."
fi

# Step 2: Create a virtual environment and install dependencies
if [ ! -d ".venv" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv .venv
fi

echo "Activating the virtual environment and installing dependencies..."
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt

# Step 3: Create the configuration file if it doesn't exist
if [ ! -f config.json ]; then
    echo "Copying config-example.json to config.json..."
    cp config-example.json config.json
fi

# Step 4: Execute the Python script
echo "Starting main.py..."
python main.py
