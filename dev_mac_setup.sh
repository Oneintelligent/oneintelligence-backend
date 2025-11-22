#!/bin/bash
set -e

# -------------------------------
# OneIntelligence Backend Dev Setup Script (macOS)
# -------------------------------
# This script sets up the development environment:
# - Installs dependencies (Homebrew, Python, PostgreSQL)
# - Creates/recreates the database
# - Sets up virtual environment
# - Installs Python packages
# - Creates .env file if needed
# - Runs migrations
# -------------------------------

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"
VENV_DIR="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"

echo "🚀 Starting OneIntelligence Backend dev setup on macOS..."
echo "📁 Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# --- Step 1: Check for Homebrew ---
if ! command -v brew &>/dev/null; then
  echo "🍺 Homebrew not found. Installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "✅ Homebrew already installed."
fi

# --- Step 2: Ensure dependencies ---
echo "📦 Ensuring Python, PostgreSQL, and Git are installed..."
brew install python postgresql git || true

# --- Step 3: Ensure PostgreSQL is running ---
echo "🟢 Checking PostgreSQL service status..."
if ! pg_isready -q; then
  echo "🟢 Starting PostgreSQL..."
  brew services start postgresql@14 || brew services start postgresql || true
  sleep 5
else
  echo "✅ PostgreSQL is already running."
fi

# --- Step 4: Recreate database (drop if exists, then create) ---
echo "🗄️  Setting up PostgreSQL database..."
CURRENT_USER=$(whoami)

# Verify we can connect to PostgreSQL
if ! psql -h localhost -U "$CURRENT_USER" -d postgres -c '\q' 2>/dev/null; then
  echo "❌ Could not connect to PostgreSQL as $CURRENT_USER."
  echo "   Please ensure PostgreSQL is running and local trust authentication is enabled."
  exit 1
fi

# Create user if it doesn't exist
if ! psql -h localhost -U "$CURRENT_USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  echo "👤 Creating PostgreSQL user $DB_USER..."
  psql -h localhost -U "$CURRENT_USER" -d postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
  echo "✅ Created PostgreSQL user $DB_USER."
else
  echo "✅ PostgreSQL user $DB_USER already exists."
fi

# Drop database if it exists (for dev, we recreate it)
if psql -h localhost -U "$CURRENT_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
  echo "🗑️  Dropping existing database $DB_NAME (dev mode)..."
  psql -h localhost -U "$CURRENT_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"
  echo "✅ Dropped existing database."
fi

# Create fresh database
echo "📦 Creating fresh database $DB_NAME..."
psql -h localhost -U "$CURRENT_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER $DB_USER;"
echo "✅ Created database $DB_NAME."

# --- Step 5: Create or reuse virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "✅ Virtual environment already exists."
fi

# Activate venv
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated."

# --- Step 6: Ensure .env file exists ---
if [ ! -f "$ENV_FILE" ]; then
  echo "🧾 Creating default .env file..."
  SECRET_KEY=$(openssl rand -hex 32)
  cat <<EOF > "$ENV_FILE"
# Django settings
DEBUG=True
SECRET_KEY=$SECRET_KEY

# Database
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=localhost
DB_PORT=5432

# Redis (optional for dev)
REDIS_URL=redis://127.0.0.1:6379/1

# OpenAI (replace with your actual key)
OPENAI_API_KEY=sk-your-openai-key-here

# Email (optional for dev)
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EOF
  echo "✅ .env file created at $ENV_FILE"
else
  echo "✅ .env file already exists."
  # Ensure required keys exist
  if ! grep -q "^SECRET_KEY=" "$ENV_FILE"; then
    SECRET_KEY=$(openssl rand -hex 32)
    echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
    echo "✅ Added SECRET_KEY to .env file."
  fi
  if ! grep -q "^DEBUG=" "$ENV_FILE"; then
    echo "DEBUG=True" >> "$ENV_FILE"
  fi
fi

# --- Step 7: Install Python dependencies ---
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "⚠️  No requirements.txt found. Installing essentials..."
  pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv django-cors-headers djangorestframework-simplejwt django-redis
fi
echo "✅ Python dependencies installed."

# --- Step 8: Run Django migrations ---
export DJANGO_SETTINGS_MODULE="config.settings"
echo "⚙️  Running Django migrations..."
python manage.py makemigrations || echo "⚠️  No new migrations to make."
python manage.py migrate
echo "✅ Django migrations complete."

# --- Step 9: Setup complete ---
echo ""
echo "🎉 Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update $ENV_FILE with your actual API keys if needed"
echo "   2. Run './dev_mac_run.sh' to start the development server"
echo ""
echo "🌐 Once running, access Swagger at: http://127.0.0.1:8000/api/schema/swagger-ui/"
echo ""
