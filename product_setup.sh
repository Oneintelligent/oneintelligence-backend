#!/bin/bash

# -------------------------------
# OneIntelligence Backend Production Setup (Ubuntu)
# -------------------------------

PROJECT_NAME="oneintelligence-backend"
PROJECT_DIR="/home/ubuntu/$PROJECT_NAME"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"
DJANGO_SETTINGS_MODULE="config.settings"
WSGI_MODULE="config.wsgi:application"
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo "🚀 Starting $PROJECT_NAME production setup on Ubuntu..."

# --- Step 0: Update system ---
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Install dependencies ---
sudo apt install python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx git curl -y

# --- Step 2: Start PostgreSQL service ---
sudo systemctl enable postgresql
sudo systemctl start postgresql

# --- Step 3: Create PostgreSQL DB and user ---
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || sudo -u postgres createdb "$DB_NAME"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;"
# --- FIX: Grant privileges on public schema ---
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;"

# --- Step 4: Check project directory ---
if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    echo "❌ manage.py not found in $PROJECT_DIR. Please place your Django project there."
    exit 1
fi

cd $PROJECT_DIR

# --- Step 5: Create/activate virtual environment ---
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# --- Step 6: Install Python dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv gunicorn
fi

# --- Step 7: Configure Django settings ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

# --- Step 8: Run migrations & collect static files ---
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# --- Step 9: Setup Gunicorn systemd service ---
GUNICORN_SERVICE="/etc/systemd/system/$PROJECT_NAME.service"
sudo bash -c "cat > $GUNICORN_SERVICE" <<EOL
[Unit]
Description=gunicorn daemon for $PROJECT_NAME
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:$PROJECT_DIR/$PROJECT_NAME.sock $WSGI_MODULE

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl start $PROJECT_NAME
sudo systemctl enable $PROJECT_NAME

# --- Step 9b: Ensure socket permissions ---
sudo chown ubuntu:www-data $PROJECT_DIR/$PROJECT_NAME.sock || true
sudo chmod 660 $PROJECT_DIR/$PROJECT_NAME.sock || true

# --- Step 10: Configure Nginx ---
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name _;  # wildcard to avoid server_name error

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root $PROJECT_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;
    }
}
EOL

sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# --- Step 11: Configure firewall ---
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "✅ Production setup complete!"
echo "Access your site at http://$EC2_PUBLIC_IP"
echo "Activate virtual environment: source venv/bin/activate"
echo "Gunicorn service: sudo systemctl status $PROJECT_NAME"
