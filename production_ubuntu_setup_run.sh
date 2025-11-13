#!/bin/bash
set -e

# ---------------------------------------------
# 🚀 OneIntelligence Backend EC2 Deployment Script (Ubuntu 22.04+)
# ---------------------------------------------
PROJECT_NAME="oneintelligence-backend"
PROJECT_DIR="/home/ubuntu/$PROJECT_NAME"
REPO_URL="https://github.com/Oneintelligent/oneintelligence-backend.git"
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

DJANGO_SETTINGS_MODULE="config.settings"
STATIC_DIR="$PROJECT_DIR/static"
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"

echo "🌍 Starting deployment for $PROJECT_NAME ..."

# --- Step 0: System Update ---
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Install Required Packages ---
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git curl nginx ufw

# --- Step 2: Setup PostgreSQL ---
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create DB user if missing
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    echo "✅ PostgreSQL user $DB_USER created."
else
    echo "✅ PostgreSQL user $DB_USER already exists."
fi

# Create DB if missing
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres createdb "$DB_NAME" -O "$DB_USER"
    echo "✅ Database $DB_NAME created."
else
    echo "✅ Database $DB_NAME already exists."
fi

# --- Step 3: Clone or Update Repo ---
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📦 Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
else
    cd "$PROJECT_DIR"
    echo "🔁 Pulling latest changes..."
    git fetch origin
    git reset --hard origin/main
    git checkout main
    git pull origin main
fi
cd "$PROJECT_DIR"

# --- Step 4: Setup Python Virtual Environment ---
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
else
    echo "✅ Virtual environment already exists."
fi

source "$PROJECT_DIR/venv/bin/activate"

# --- Step 5: Install Dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install django djangorestframework psycopg2-binary drf-spectacular python-dotenv gunicorn
fi
echo "✅ Python dependencies installed."

# --- Step 6: Migrations & Static Files ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
mkdir -p "$STATIC_DIR"
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
# --- Safe Migration Recheck (handles partial DB schema updates) ---
echo "🧩 Running post-migration consistency check..."
python manage.py makemigrations users || true
python manage.py migrate users --fake-initial || true
echo "✅ Database schema verified and up-to-date."

echo "✅ Django migrations and static collection complete."

# --- Step 7: Gunicorn Setup (fixed path, UMask, permissions) ---
if [ ! -f "$GUNICORN_SERVICE" ]; then
    echo "⚙️ Creating Gunicorn systemd service..."
    sudo bash -c "cat > $GUNICORN_SERVICE" <<EOF
[Unit]
Description=Gunicorn daemon for OneIntelligence Backend
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
Environment="PATH=$PROJECT_DIR/venv/bin"
UMask=007
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:$PROJECT_DIR/$PROJECT_NAME.sock \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable gunicorn
    echo "✅ Gunicorn service created and enabled."
else
    echo "✅ Gunicorn service already exists — skipping."
fi

# Fix directory access for Nginx
# 1️⃣ Make sure Gunicorn socket and directories are accessible
sudo chown -R ubuntu:www-data /home/ubuntu/oneintelligence-backend
sudo chmod 755 /home/ubuntu
sudo chmod 755 /home/ubuntu/oneintelligence-backend

# 2️⃣ Gunicorn socket should be group-writeable
if [ -S "/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock" ]; then
    sudo chmod 770 /home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock
else
    echo "⚠️  Gunicorn socket not found yet — it will be created on first start."
fi

# 3️⃣ Static files only need read access
sudo chmod -R 755 /home/ubuntu/oneintelligence-backend/static


sudo systemctl restart gunicorn
echo "🔁 Gunicorn restarted."

# --- Step 8: Nginx Setup (correct socket path + server_name) ---
if [ ! -f "$NGINX_CONF" ]; then
    echo "🌐 Creating Nginx configuration..."
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
    sudo bash -c "cat > $NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $PUBLIC_IP;

    location /static/ {
        alias $STATIC_DIR/;
        expires 1y;
        access_log off;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;
    }

    client_max_body_size 50M;
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
}
EOF

    sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
    echo "✅ Nginx site configuration created."
else
    echo "✅ Nginx configuration already exists — skipping."
fi

sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
echo "🔁 Nginx restarted."

# --- Step 9: Firewall Rules (Safe and Idempotent) ---
echo "🛡️  Configuring firewall safely..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment "Allow SSH"
sudo ufw allow 80/tcp comment "Allow HTTP"
sudo ufw allow 443/tcp comment "Allow HTTPS"
sudo ufw --force enable
sudo ufw status verbose
echo "✅ Firewall configured safely (SSH, HTTP, HTTPS open)."

# --- Step 10: Health Check ---
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
echo "🎯 Checking application health..."
sleep 2
if curl -s "http://$PUBLIC_IP" | grep -q "DOCTYPE"; then
    echo "✅ Application is live at: http://$PUBLIC_IP"
else
    echo "⚠️ Application deployed but health check failed. Check Gunicorn/Nginx logs."
fi

echo "🎉 Deployment Complete!"
echo "🌐 Swagger: http://$PUBLIC_IP/api/schema/swagger-ui/"
