#!/bin/bash
set -e

# -------------------------------
# OneIntelligence Backend Local Setup Script (macOS)
# -------------------------------

PROJECT_NAME="oneintelligence-backend"
PROJECT_DIR="$HOME/$PROJECT_NAME"
REPO_URL="https://github.com/Oneintelligent/oneintelligence-backend.git"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

DJANGO_SETTINGS_MODULE="config.settings"
STATIC_DIR="$PROJECT_DIR/static"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 Starting $PROJECT_NAME local setup on macOS..."

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

# --- Step 4: Verify connection before attempting DB setup ---
echo "🧠 Verifying PostgreSQL connection..."
if ! psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
  echo "⚙️  Setting up PostgreSQL database and user..."
  CURRENT_USER=$(whoami)

  if ! psql -h localhost -U "$CURRENT_USER" -d postgres -c '\q' 2>/dev/null; then
    echo "❌ Could not connect to PostgreSQL as $CURRENT_USER. Please ensure local trust authentication is enabled."
    exit 1
  fi

  if ! psql -h localhost -U "$CURRENT_USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    psql -h localhost -U "$CURRENT_USER" -d postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    echo "✅ Created PostgreSQL user $DB_USER."
  else
    echo "✅ PostgreSQL user $DB_USER already exists."
  fi

  if ! psql -h localhost -U "$CURRENT_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    psql -h localhost -U "$CURRENT_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER $DB_USER;"
    echo "✅ Created database $DB_NAME."
  else
    echo "✅ Database $DB_NAME already exists."
  fi
else
  echo "✅ Verified connection to existing database $DB_NAME."
fi

# --- Step 5: Clone or update repository ---
if [ ! -d "$PROJECT_DIR" ]; then
  echo "📦 Cloning repository..."
  git clone "$REPO_URL" "$PROJECT_DIR"
else
  cd "$PROJECT_DIR"
  echo "🔁 Pulling latest changes from main branch..."
  git reset --hard
  git checkout main
  git pull origin main
fi
cd "$PROJECT_DIR"

# --- Step 6: Create or reuse virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "✅ Virtual environment already exists."
fi

# Activate venv (universal)
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated."

# --- Step 7: Ensure .env file exists ---
if [ ! -f ".env" ]; then
  echo "🧾 Creating default .env file..."
  cat <<EOF > .env
# Django settings
DEBUG=True
SECRET_KEY=your_local_secret_key

# Database
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=localhost
DB_PORT=5432

# OpenAI (replace with your actual key)
OPENAI_API_KEY=sk-your-openai-key-here
EOF
  echo "✅ .env file created at $PROJECT_DIR/.env"
else
  echo "✅ .env file already exists."
fi

# --- Step 8: Install Python dependencies ---
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv
fi
echo "✅ Python dependencies installed."

# --- Step 9: Django setup ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
mkdir -p "$STATIC_DIR"

echo "⚙️ Running Django migrations..."
echo "🧹 Skipping collectstatic for local development..."
python manage.py makemigrations
python manage.py migrate
echo "✅ Django migrations complete."

# --- Step 10: Run development server ---
echo "🚀 Setup complete!"
echo "🌐 Starting Django development server..."
echo "Visit: http://127.0.0.1:8000/api/schema/swagger-ui/"
python manage.py runserver
