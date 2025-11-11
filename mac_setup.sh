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

echo "🚀 Starting $PROJECT_NAME local setup on macOS..."

# --- Step 1: Check for Homebrew ---
if ! command -v brew &>/dev/null; then
  echo "🍺 Homebrew not found. Installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "✅ Homebrew already installed."
fi

# --- Step 2: Install dependencies ---
echo "📦 Installing Python, PostgreSQL, and Git..."
brew install python postgresql git || true

# --- Step 3: Start PostgreSQL ---
echo "🟢 Starting PostgreSQL..."
brew services start postgresql

# --- Step 4: Setup PostgreSQL database ---
echo "🛠 Setting up PostgreSQL database and user..."
if ! psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  psql postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
  echo "✅ PostgreSQL user $DB_USER created."
else
  echo "✅ PostgreSQL user $DB_USER exists."
fi

if ! psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
  createdb "$DB_NAME" -O "$DB_USER"
  echo "✅ Database $DB_NAME created."
else
  echo "✅ Database $DB_NAME exists."
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

# --- Step 6: Setup Python virtual environment ---
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv venv
else
  echo "✅ Virtual environment exists."
fi
source venv/bin/activate

# --- Step 7: Install Python dependencies ---
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv
fi
echo "✅ Python dependencies installed."

# --- Step 8: Django setup ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
mkdir -p "$STATIC_DIR"

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
echo "✅ Django migrations complete."

# --- Step 9: Run development server ---
echo "🚀 Setup complete!"
echo "🌐 Starting Django development server..."
echo "Visit: http://127.0.0.1:8000/api/schema/swagger-ui/"
python manage.py runserver
