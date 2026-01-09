#!/bin/bash
# WBSEDCL Tracking System - Environment Setup Script

echo "=========================================="
echo "WBSEDCL Tracking System - Setup"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "wbsedcl_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv wbsedcl_env
    
    if [ $? -eq 0 ]; then
        echo "✓ Virtual environment created successfully"
    else
        echo "✗ Failed to create virtual environment"
        exit 1
    fi
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source wbsedcl_env/bin/activate

if [ $? -eq 0 ]; then
    echo "✓ Virtual environment activated"
else
    echo "✗ Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "✓ All dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

# Display installed packages
echo ""
echo "=========================================="
echo "Installed Packages:"
echo "=========================================="
pip list

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment manually:"
echo "  source wbsedcl_env/bin/activate"
echo ""
echo "To deactivate:"
echo "  deactivate"
echo ""
echo "To initialize the database:"
echo "  python init_database.py"
echo ""
echo "=========================================="
