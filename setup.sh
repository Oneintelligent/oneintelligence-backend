#!/bin/bash
set -e

# -------------------------------
# OneIntelligence Backend EC2 Update Script (Ubuntu)
# -------------------------------

# --- Configuration ---
PROJECT_NAME="oneintelligence-backend"
PROJECT_DIR="/home/ubuntu/$PROJECT_NAME"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

DJANGO_SETTINGS_MODULE="config.settings"
APP_PORT=8000

echo "🚀 Starting $PROJECT_NAME update..."

# --- Step 0: Update system ---
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Install dependencies if missing ---
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git curl ufw

# --- Step 2: Pull latest code from main branch ---
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    echo "🔁 Pulling latest code from main branch..."
    git reset --hard
    git checkout main
    git pull origin main
else
    echo "❌ Project directory $PROJECT_DIR not found. Please clone repo manually first."
    exit 1
fi

# --- Step 3: Create/Activate virtual environment ---
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Virtual environment not found. Creating..."
    python3 -m venv "$PROJECT_DIR/venv"
fi
source "$PROJECT_DIR/venv/bin/activate"

# --- Step 4: Install/update Python dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv gunicorn
fi

# --- Step 5: Run Django migrations & collect static ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

echo "✅ Django updated successfully."

# --- Step 6: Create/Update Gunicorn systemd service ---
GUNICORN_SERVICE_FILE="/etc/systemd/system/$PROJECT_NAME.service"

sudo bash -c "cat > $GUNICORN_SERVICE_FILE" <<EOL
[Unit]
Description=Gunicorn service for $PROJECT_NAME
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=\"DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE\"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind unix:$PROJECT_DIR/$PROJECT_NAME.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable "$PROJECT_NAME"
sudo systemctl restart "$PROJECT_NAME"
echo "✅ Gunicorn restarted with virtual environment."

# --- Step 7: Restart Nginx ---
sudo systemctl restart nginx
echo "✅ Nginx restarted."

# --- Step 8: Finish ---
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
echo "🎉 Update complete!"
echo "🌐 Visit: http://$PUBLIC_IP"
echo "📘 Swagger UI: http://$PUBLIC_IP/api/schema/swagger-ui/"
