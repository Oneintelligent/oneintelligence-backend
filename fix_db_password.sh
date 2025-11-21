#!/bin/bash
# Quick fix for DB_PASSWORD missing in production
# Run this script on your production server

set -e

PROJECT_DIR="/home/ubuntu/oneintelligence-backend"
ENV_FILE="$PROJECT_DIR/.env"

echo "🔐 Fixing DB_PASSWORD in .env file..."

# Ensure .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "📝 Creating .env file..."
    touch "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# Check if DB_PASSWORD exists
if grep -q "^DB_PASSWORD=" "$ENV_FILE" 2>/dev/null; then
    echo "✅ DB_PASSWORD already exists in .env file"
    echo "Current value: $(grep '^DB_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2 | head -c 10)..."
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing DB_PASSWORD"
        exit 0
    fi
    # Remove old DB_PASSWORD line
    sed -i '/^DB_PASSWORD=/d' "$ENV_FILE"
fi

# Add/Update DB_PASSWORD (using the default from deployment script)
DB_PASSWORD="Onei@123"
echo "DB_PASSWORD=$DB_PASSWORD" >> "$ENV_FILE"

# Also ensure other DB variables exist
if ! grep -q "^DB_NAME=" "$ENV_FILE" 2>/dev/null; then
    echo "DB_NAME=oneintelligence-db" >> "$ENV_FILE"
fi
if ! grep -q "^DB_USER=" "$ENV_FILE" 2>/dev/null; then
    echo "DB_USER=oneintelligence" >> "$ENV_FILE"
fi
if ! grep -q "^DB_HOST=" "$ENV_FILE" 2>/dev/null; then
    echo "DB_HOST=localhost" >> "$ENV_FILE"
fi
if ! grep -q "^DB_PORT=" "$ENV_FILE" 2>/dev/null; then
    echo "DB_PORT=5432" >> "$ENV_FILE"
fi

# Set secure permissions
chmod 600 "$ENV_FILE"
chown ubuntu:ubuntu "$ENV_FILE"

echo "✅ DB_PASSWORD and other DB variables have been set in $ENV_FILE"
echo ""
echo "📋 Next steps:"
echo "1. Test Django: cd $PROJECT_DIR && source venv/bin/activate && python manage.py check"
echo "2. Restart Gunicorn: sudo systemctl restart gunicorn"
echo "3. Check Gunicorn status: sudo systemctl status gunicorn"

