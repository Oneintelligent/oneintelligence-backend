#!/bin/bash
set -e

# -------------------------------
# OneIntelligence Backend EC2 Full Deployment Script (Ubuntu)
# -------------------------------

# --- Configuration ---
PROJECT_NAME="oneintelligence-backend"
PROJECT_DIR="/home/ubuntu/$PROJECT_NAME"
REPO_URL="https://github.com/Oneintelligent/oneintelligence-backend.git"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

DJANGO_SETTINGS_MODULE="config.settings"
APP_PORT=8000
SERVER_NAME="13.201.192.254"

STATIC_DIR="$PROJECT_DIR/static"

echo "🚀 Starting $PROJECT_NAME full deployment..."

# --- Step 0: Update system ---
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Install dependencies ---
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git curl ufw

# --- Step 2: Setup PostgreSQL ---
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create DB user if missing
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    echo "✅ PostgreSQL user $DB_USER created."
else
    echo "✅ PostgreSQL user $DB_USER exists."
fi

# Create DB if missing
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres createdb "$DB_NAME" -O "$DB_USER"
    echo "✅ Database $DB_NAME created."
else
    echo "✅ Database $DB_NAME exists."
fi

# Set role configs
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
echo "✅ PostgreSQL role configuration applied."

# --- Step 3: Clone or pull repo ---
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

# --- Step 4: Setup Python virtual environment ---
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
else
    echo "✅ Virtual environment exists."
fi
source "$PROJECT_DIR/venv/bin/activate"

# --- Step 5: Install Python dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv gunicorn
fi
echo "✅ Python dependencies installed."

# --- Step 6: Django migrations & collect static ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

# Ensure STATIC_ROOT exists
mkdir -p "$STATIC_DIR"

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
echo "✅ Django migrations & static files complete."

# --- Step 7: Configure Gunicorn systemd service ---
GUNICORN_SERVICE_FILE="/etc/systemd/system/$PROJECT_NAME.service"

sudo bash -c "cat > $GUNICORN_SERVICE_FILE" <<EOL
[Unit]
Description=Gunicorn service for $PROJECT_NAME
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:$APP_PORT config.wsgi:application

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable "$PROJECT_NAME"
sudo systemctl restart "$PROJECT_NAME"
echo "✅ Gunicorn started/restarted."

# --- Step 8: Configure Nginx ---
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"

sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name $SERVER_NAME;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias $STATIC_DIR/;
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:$APP_PORT;
    }
}
EOL

sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
echo "✅ Nginx configured and restarted."

# --- Step 9: Configure Firewall ---
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
echo "✅ Firewall rules applied."

# --- Step 10: Finish ---
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
echo "🎉 Deployment complete!"
echo "🌐 Swagger UI: http://$PUBLIC_IP/api/schema/swagger-ui/"
