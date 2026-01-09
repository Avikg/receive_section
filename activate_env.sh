#!/bin/bash
# WBSEDCL Tracking System - Linux/Mac Activation Script

echo "=========================================="
echo "WBSEDCL Tracking System"
echo "=========================================="
echo ""

if [ ! -d "wbsedcl_env" ]; then
    echo "Virtual environment not found!"
    echo "Please run setup_env.sh first"
    echo ""
    echo "  bash setup_env.sh"
    echo ""
    exit 1
fi

echo "Activating virtual environment..."
source wbsedcl_env/bin/activate

if [ $? -eq 0 ]; then
    echo "✓ Virtual environment activated"
    echo ""
    echo "=========================================="
    echo "Environment Information:"
    echo "=========================================="
    echo "Python: $(python --version)"
    echo "Pip: $(pip --version)"
    echo ""
    echo "To deactivate, run:"
    echo "  deactivate"
    echo ""
    echo "=========================================="
else
    echo "✗ Failed to activate virtual environment"
    exit 1
fi

# Keep the shell active in the virtual environment
exec bash
