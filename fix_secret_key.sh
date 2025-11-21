#!/bin/bash
# Fix SECRET_KEY issue in production
# Run this script on your production server

set -e

PROJECT_DIR="/home/ubuntu/oneintelligence-backend"
ENV_FILE="$PROJECT_DIR/.env"

echo "🔐 Setting up SECRET_KEY for production..."

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "📝 Creating .env file..."
    touch "$ENV_FILE"
    chmod 600 "$ENV_FILE"  # Secure permissions
fi

# Check if SECRET_KEY already exists in .env
if grep -q "^SECRET_KEY=" "$ENV_FILE" 2>/dev/null; then
    echo "✅ SECRET_KEY already exists in .env file"
    echo "Current SECRET_KEY: $(grep '^SECRET_KEY=' "$ENV_FILE" | cut -d'=' -f2 | head -c 20)..."
    read -p "Do you want to generate a new SECRET_KEY? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing SECRET_KEY"
        exit 0
    fi
    # Remove old SECRET_KEY line
    sed -i '/^SECRET_KEY=/d' "$ENV_FILE"
fi

# Generate new SECRET_KEY
echo "🔑 Generating new SECRET_KEY..."
NEW_SECRET_KEY=$(openssl rand -hex 32)

# Add SECRET_KEY to .env file
echo "SECRET_KEY=$NEW_SECRET_KEY" >> "$ENV_FILE"

# Also set DEBUG if not present
if ! grep -q "^DEBUG=" "$ENV_FILE" 2>/dev/null; then
    echo "DEBUG=False" >> "$ENV_FILE"
fi

# Set secure permissions
chmod 600 "$ENV_FILE"
chown ubuntu:ubuntu "$ENV_FILE"

echo "✅ SECRET_KEY has been set in $ENV_FILE"
echo "✅ File permissions set to 600 (read/write for owner only)"

# Export for current session
export SECRET_KEY="$NEW_SECRET_KEY"
echo "✅ SECRET_KEY exported for current session"

echo ""
echo "📋 Next steps:"
echo "1. Restart Gunicorn: sudo systemctl restart gunicorn"
echo "2. Check Gunicorn status: sudo systemctl status gunicorn"
echo "3. Test Django: cd $PROJECT_DIR && source venv/bin/activate && python manage.py check"

