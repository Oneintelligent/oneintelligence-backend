#!/bin/bash
set -e

################################################################################
# dev_mac_run.sh
# -------------------------------------------------
# One-click runner for your Django + PostgreSQL backend on macOS.
# Handles:
#   ✅ Virtual environment activation
#   ✅ PostgreSQL check and start
#   ✅ Dependency verification
#   ✅ makemigrations + migrate
#   ✅ Server start
################################################################################

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
ENV_FILE="$PROJECT_DIR/.env"

echo "🔹 Starting Django project from: $PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# -----------------------------
# STEP 1 — Check PostgreSQL
# -----------------------------
echo "🧠 Checking PostgreSQL installation..."

if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found on this system."
    echo "➡️  You can install it with: brew install postgresql"
    echo "   Or run './dev_mac_setup.sh' to set up everything."
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready &> /dev/null; then
    echo "⚙️  PostgreSQL is installed but not running. Starting service..."
    brew services start postgresql@14 || brew services start postgresql || true
    sleep 3
    if ! pg_isready &> /dev/null; then
        echo "❌ Failed to start PostgreSQL. Please start it manually."
        exit 1
    fi
else
    echo "✅ PostgreSQL is running."
fi

# -----------------------------
# STEP 2 — Check virtual environment
# -----------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found at $VENV_DIR"
    echo "➡️  Please run './dev_mac_setup.sh' first to set up the project."
    exit 1
fi

source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated."

# -----------------------------
# STEP 3 — Verify dependencies
# -----------------------------
echo "📦 Verifying dependencies..."

if ! python -c "import django" &> /dev/null; then
    echo "⚠️  Django not found. Installing dependencies..."
    pip install --upgrade pip >/dev/null
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE"
    else
        echo "⚠️  No requirements.txt found. Installing essentials..."
        pip install django djangorestframework drf-spectacular psycopg2-binary python-dotenv django-cors-headers djangorestframework-simplejwt django-redis
    fi
else
    echo "✅ Dependencies are installed."
fi

# -----------------------------
# STEP 4 — Check .env file
# -----------------------------
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env file not found. Creating a basic one..."
    SECRET_KEY=$(openssl rand -hex 32)
    cat <<EOF > "$ENV_FILE"
DEBUG=True
SECRET_KEY=$SECRET_KEY
DB_NAME=oneintelligence-db
DB_USER=oneintelligence
DB_PASSWORD=Onei@123
DB_HOST=localhost
DB_PORT=5432
EOF
    echo "✅ Created basic .env file. You may want to update it with your API keys."
fi

# -----------------------------
# STEP 5 — Run migrations
# -----------------------------
export DJANGO_SETTINGS_MODULE="config.settings"
echo "🧩 Running makemigrations and migrate..."
python manage.py makemigrations || echo "⚠️  No new migrations to make."
python manage.py migrate || { echo "❌ migrate failed!"; exit 1; }
echo "✅ Migrations complete."

# -----------------------------
# STEP 6 — Run server
# -----------------------------
echo ""
echo "🚀 Starting Django development server..."
echo "🌐 Access Swagger at: http://127.0.0.1:8000/api/schema/swagger-ui/"
echo "📝 Press Ctrl+C to stop the server"
echo ""
python manage.py runserver
