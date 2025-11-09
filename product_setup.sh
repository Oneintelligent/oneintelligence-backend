#!/bin/bash
set -e

# -------------------------------
# OneIntelligence Backend Production Setup (Ubuntu)
# -------------------------------

# --- Configuration ---
PROJECT_NAME="oneintelligence-backend"
PROJECT_DIR="/home/ubuntu/$PROJECT_NAME"
REPO_URL="https://github.com/Oneintelligent/oneintelligence-backend.git"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"
DJANGO_SETTINGS_MODULE="config.settings"
WSGI_MODULE="config.wsgi:application"
STATIC_DIR="$PROJECT_DIR/static"

# --- Define server name / IP here ---
SERVER_NAME="3.109.211.100"

echo "🚀 Starting $PROJECT_NAME production setup on $SERVER_NAME..."

# --- Step 0: Update system ---
echo "📦 Updating system..."
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Install dependencies ---
echo "📦 Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx git curl ufw

# --- Step 2: Start PostgreSQL service ---
echo "🗄️  Starting PostgreSQL service..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# --- Step 3: PostgreSQL DB/User setup ---
echo "🗄️  Configuring PostgreSQL DB and user..."
# Create user if missing
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

# Ensure schema ownership & privileges
echo "🔧 Setting schema permissions..."
sudo -u postgres psql -d "$DB_NAME" -c "ALTER SCHEMA public OWNER TO $DB_USER;"
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO $DB_USER;"

# Set role configs
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
echo "✅ PostgreSQL role and schema configuration applied."

# --- Step 4: Clone or update project ---
echo "📂 Setting up project directory..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📦 Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
else
    cd "$PROJECT_DIR"
    echo "🔁 Pulling latest changes..."
    git reset --hard
    git checkout main
    git pull origin main
fi
cd "$PROJECT_DIR"

# --- Step 5: Setup Python virtual environment ---
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
else
    echo "✅ Virtual environment exists."
fi
source "$PROJECT_DIR/venv/bin/activate"

# --- Step 6: Install Python dependencies ---
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv gunicorn
fi
echo "✅ Python dependencies installed."

# --- Step 7: Django migrations & collect static ---
echo "🛠️  Running Django migrations and collecting static files..."
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
mkdir -p "$STATIC_DIR"
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
echo "✅ Django migrations and static files complete."

# --- Step 8: Setup Gunicorn systemd service ---
echo "⚙️  Setting up Gunicorn systemd service..."
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

# --- Step 8b: Ensure socket permissions ---
sudo chown ubuntu:www-data $PROJECT_DIR/$PROJECT_NAME.sock || true
sudo chmod 660 $PROJECT_DIR/$PROJECT_NAME.sock || true

# --- Step 9: Configure Nginx ---
echo "🌐 Configuring Nginx..."
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name $SERVER_NAME;

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

# --- Step 10: Configure firewall ---
echo "🔒 Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "✅ Production setup complete!"
echo "Access your site at http://$SERVER_NAME"
echo "Activate virtual environment: source venv/bin/activate"
echo "Gunicorn service: sudo systemctl status $PROJECT_NAME"
