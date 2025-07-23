#!/bin/bash
echo "Setting up Revolut & WDO Platform..."
mkdir -p revolut_wdo/app/routes revolut_wdo/app/utils revolut_wdo/app/templates revolut_wdo/static/css
touch revolut_wdo/__init__.py
cd revolut_wdo
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Installing requirements..."
pip install -r requirements.txt
echo "Setup complete."
