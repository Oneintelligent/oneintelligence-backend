#!/bin/bash
# Script to validate onboarding API - run this from the backend directory

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Run the validation script
python3 validate_onboarding_api.py

