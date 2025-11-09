#!/bin/bash

# -------------------------------
# OneIntelligence Backend Setup (Ubuntu)
# -------------------------------

PROJECT_NAME="oneintelligence-backend"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

echo "🚀 Starting $PROJECT_NAME setup on Ubuntu..."

# --- Step 0: Update system ---
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Check Python3 ---
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Installing..."
    sudo apt install python3 -y
fi

# --- Step 2: Check pip ---
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found. Installing..."
    sudo apt install python3-pip -y
fi

# --- Step 3: Check PostgreSQL ---
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL not found. Installing..."
    sudo apt install postgresql postgresql-contrib -y
fi

# Start PostgreSQL service
sudo systemctl enable postgresql
sudo systemctl start postgresql

# --- Step 4: Enter project directory ---
if [ ! -f "manage.py" ]; then
    echo "❌ manage.py not found. Please run this script inside your Django project root."
    exit 1
fi

# --- Step 5: Create/activate virtual environment ---
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# --- Step 6: Install dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv gunicorn
fi

# --- Step 7: Create PostgreSQL DB and user ---
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || sudo -u postgres createdb "$DB_NAME"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;"

# --- Step 8: Export Django settings ---
export DJANGO_SETTINGS_MODULE=config.settings

# --- Step 9: Run Django migrations ---
python manage.py makemigrations
python manage.py migrate

echo "✅ Setup complete!"
echo "Activate virtual environment: source venv/bin/activate"
echo "Run server: python manage.py runserver 0.0.0.0:8000"
echo "Swagger UI: http://<your-ec2-public-ip>:8000/api/schema/swagger-ui/"
