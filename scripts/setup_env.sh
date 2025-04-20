#!/bin/bash
# setup_env.sh

# Define the virtual environment directory
VENV_DIR="$HOME/aix_env"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR."
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install requests gitpython pytest flask pandas github3.py psutil autopep8

# Install Node.js and npm if not already installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Installing Node.js..."
    brew install node || {
        echo "Homebrew not found or failed to install Node.js. Please install Node.js manually."
        exit 1
    }
else
    echo "Node.js is already installed."
fi

# Install Julia if not already installed
if ! command -v julia &> /dev/null; then
    echo "Julia is not installed. Installing Julia..."
    brew install julia || {
        echo "Homebrew not found or failed to install Julia. Please install Julia manually."
        exit 1
    }
else
    echo "Julia is already installed."
fi

echo "Virtual environment setup complete. Activate it with: source $VENV_DIR/bin/activate"