#!/bin/bash

# Launch script for chat_py2 application
# This script can be run from anywhere

# Hardcoded path to the chat application
SCRIPT_DIR="/home/mic/SharedDrive/Python Projects/chat_py2"

# Initialize conda for bash (if not already done)
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
    echo "Error: Miniconda not found at $HOME/miniconda3"
    echo "Please ensure Miniconda is installed."
    exit 1
fi

# Activate the chat_py2 environment
echo "Activating chat_py2 environment..."
conda activate chat_py2

if [ $? -ne 0 ]; then
    echo "Error: Failed to activate chat_py2 environment"
    echo "Please ensure the environment exists: conda env list"
    exit 1
fi

# Change to the application directory
cd "$SCRIPT_DIR"

# Launch the application
echo "Starting chat application..."
python main.py

# Deactivate conda environment after the app closes
conda deactivate
