#!/bin/bash

# -------------------------------
# OneIntelligence Backend Setup
# -------------------------------

PROJECT_NAME="oneintelligence-backend"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

# --- Step 0: Check Python3 ---
if ! command -v python3 &> /dev/null
then
    echo "Python3 not found. Please install Python3 first."
    exit 1
fi

# --- Step 1: Check pip ---
if ! command -v pip3 &> /dev/null
then
    echo "pip3 not found. Please install pip3 first."
    exit 1
fi

# --- Step 2: Check PostgreSQL ---
if ! command -v psql &> /dev/null
then
    echo "PostgreSQL not found. Installing via Homebrew..."
    brew install postgresql
fi

# Start PostgreSQL service
brew services start postgresql

# --- Step 3: Enter project directory ---
if [ ! -f "manage.py" ]; then
    echo "manage.py not found. Please checkout the repo first."
    exit 1
fi

# --- Step 4: Create/activate virtual environment ---
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# --- Step 5: Install dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular
fi

# --- Step 6: Set Django settings module ---
export DJANGO_SETTINGS_MODULE=config.settings

# --- Step 7: Create PostgreSQL DB and user if missing ---
DB_EXISTS=$(psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
if [ "$DB_EXISTS" != "1" ]; then
    createdb "$DB_NAME"
    echo "Database $DB_NAME created."
else
    echo "Database $DB_NAME already exists."
fi

USER_EXISTS=$(psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'")
if [ "$USER_EXISTS" != "1" ]; then
    psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    echo "User $DB_USER created."
else
    echo "User $DB_USER already exists."
fi

# Set role configs and grant privileges
psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;"

# --- Step 8: Run Django migrations ---
python manage.py makemigrations
python manage.py migrate

echo "✅ Setup complete!"
echo "Activate virtual environment: source venv/bin/activate"
echo "Run server: python manage.py runserver"
echo "Swagger UI: http://127.0.0.1:8000/api/schema/swagger-ui/"
