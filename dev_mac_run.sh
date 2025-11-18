#!/bin/bash

################################################################################
# dev_mac_run.sh
# -------------------------------------------------
# One-click runner for your Django + PostgreSQL backend on macOS.
# Handles:
#   ✅ Virtual environment setup
#   ✅ Dependency installation
#   ✅ PostgreSQL check and start
#   ✅ makemigrations + migrate
#   ✅ Server start
################################################################################

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

echo "🔹 Starting Django project from: $PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# -----------------------------
# STEP 1 — Check PostgreSQL
# -----------------------------
echo "🧠 Checking PostgreSQL installation..."

if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found on this system."
    echo "➡️  You can install it with: brew install postgresql"
    read -p "Do you want me to install PostgreSQL now? (y/n): " INSTALL_PG
    if [[ "$INSTALL_PG" =~ ^[Yy]$ ]]; then
        brew install postgresql
    else
        echo "⚠️  PostgreSQL is required. Exiting..."
        exit 1
    fi
fi

# Check if PostgreSQL is running
if ! pg_isready &> /dev/null; then
    echo "⚙️  PostgreSQL is installed but not running. Starting service..."
    brew services start postgresql
    sleep 2
else
    echo "✅ PostgreSQL is running."
fi

# -----------------------------
# STEP 2 — Activate or create venv
# -----------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️  Virtual environment not found. Creating one..."
    python3 -m venv .venv
fi

source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated."

# -----------------------------
# STEP 3 — Install dependencies
# -----------------------------
echo "📦 Installing dependencies..."
pip install --upgrade pip >/dev/null

if [ -f "$REQUIREMENTS_FILE" ]; then
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "⚠️ No requirements.txt found. Installing essentials..."
    pip install django djangorestframework drf-spectacular psycopg2-binary python-dotenv
fi

# Verify Django installed
if ! python -c "import django" &> /dev/null; then
    echo "❌ Django not found, installing manually..."
    pip install django
else
    echo "✅ Django is installed."
fi

# -----------------------------
# STEP 4 — Run migrations
# -----------------------------
# echo "🧩 Running makemigrations and migrate..."
# python manage.py makemigrations || { echo "❌ makemigrations failed!"; exit 1; }
# python manage.py migrate || { echo "❌ migrate failed!"; exit 1; }

# -----------------------------
# STEP 5 — Run server
# -----------------------------
echo "🚀 Starting Django development server..."
echo "🌐 Access Swagger at: http://127.0.0.1:8000/api/schema/swagger-ui/"
python manage.py runserver
