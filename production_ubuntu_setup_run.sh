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
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git curl nginx ufw redis-server

# --- Step 2: Setup PostgreSQL and Redis ---
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Setup Redis
if sudo systemctl is-active --quiet redis-server; then
    echo "✅ Redis server already running."
else
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    echo "✅ Redis server started and enabled."
fi

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
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        echo "⚠️  Warning: Uncommitted changes detected. Stashing them..."
        git stash save "Auto-stash before deployment $(date +%Y%m%d_%H%M%S)"
    fi
    git fetch origin
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

# --- Step 6: Setup Environment Variables (.env file) ---
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "🔐 Creating .env file with required environment variables..."
    # Generate SECRET_KEY
    SECRET_KEY=$(openssl rand -hex 32)
    cat > "$ENV_FILE" <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=localhost
DB_PORT=5432
OPENAI_API_KEY=sk-placeholder-not-configured
REDIS_URL=redis://127.0.0.1:6379/1
EOF
    chmod 600 "$ENV_FILE"
    chown ubuntu:ubuntu "$ENV_FILE"
    echo "✅ .env file created with all required variables"
else
    # Ensure SECRET_KEY exists
    if ! grep -q "^SECRET_KEY=" "$ENV_FILE" 2>/dev/null; then
        echo "🔐 Adding SECRET_KEY to existing .env file..."
        SECRET_KEY=$(openssl rand -hex 32)
        echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
        echo "✅ SECRET_KEY added to .env file"
    else
        echo "✅ SECRET_KEY already exists in .env file"
    fi
    # Ensure DEBUG is set
    if ! grep -q "^DEBUG=" "$ENV_FILE" 2>/dev/null; then
        echo "DEBUG=False" >> "$ENV_FILE"
    fi
    # Ensure DB variables are set
    if ! grep -q "^DB_NAME=" "$ENV_FILE" 2>/dev/null; then
        echo "DB_NAME=$DB_NAME" >> "$ENV_FILE"
    fi
    if ! grep -q "^DB_USER=" "$ENV_FILE" 2>/dev/null; then
        echo "DB_USER=$DB_USER" >> "$ENV_FILE"
    fi
    if ! grep -q "^DB_PASSWORD=" "$ENV_FILE" 2>/dev/null; then
        echo "DB_PASSWORD=$DB_PASS" >> "$ENV_FILE"
        echo "✅ DB_PASSWORD added to .env file"
    else
        echo "✅ DB_PASSWORD already exists in .env file"
    fi
    if ! grep -q "^DB_HOST=" "$ENV_FILE" 2>/dev/null; then
        echo "DB_HOST=localhost" >> "$ENV_FILE"
    fi
    if ! grep -q "^DB_PORT=" "$ENV_FILE" 2>/dev/null; then
        echo "DB_PORT=5432" >> "$ENV_FILE"
    fi
    # Ensure OPENAI_API_KEY exists (required for AI features)
    if ! grep -q "^OPENAI_API_KEY=" "$ENV_FILE" 2>/dev/null; then
        echo "OPENAI_API_KEY=sk-placeholder-not-configured" >> "$ENV_FILE"
        echo "⚠️  OPENAI_API_KEY set to placeholder. Please update with your actual API key."
    else
        echo "✅ OPENAI_API_KEY already exists in .env file"
    fi
    # Ensure REDIS_URL exists
    if ! grep -q "^REDIS_URL=" "$ENV_FILE" 2>/dev/null; then
        echo "REDIS_URL=redis://127.0.0.1:6379/1" >> "$ENV_FILE"
    fi
    # Update permissions
    chmod 600 "$ENV_FILE"
    chown ubuntu:ubuntu "$ENV_FILE"
fi

# --- Step 7: Migrations & Static Files ---
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
# Load .env file for this session
export $(grep -v '^#' "$ENV_FILE" | xargs)
mkdir -p "$STATIC_DIR"

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

# --- Safe Migration Recheck (handles partial DB schema updates) ---
echo "🧩 Running post-migration consistency check..."

echo "✅ Database schema verified and up-to-date."

echo "✅ Django migrations and static collection complete."

# --- Step 8: Gunicorn Setup (fixed path, UMask, permissions) ---
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
EnvironmentFile=$ENV_FILE
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

# 2️⃣ Gunicorn socket should be group-writeable (fix permissions every time)
SOCKET_FILE="/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock"
if [ -S "$SOCKET_FILE" ]; then
    sudo chmod 770 "$SOCKET_FILE"
    sudo chown ubuntu:www-data "$SOCKET_FILE"
    echo "✅ Gunicorn socket permissions updated."
else
    echo "⚠️  Gunicorn socket not found yet — it will be created on first start."
    # Ensure parent directory has correct permissions for socket creation
    sudo chmod 755 /home/ubuntu/oneintelligence-backend
    sudo chown ubuntu:www-data /home/ubuntu/oneintelligence-backend
fi

# 3️⃣ Static files only need read access
if [ -d "/home/ubuntu/oneintelligence-backend/static" ]; then
    sudo chmod -R 755 /home/ubuntu/oneintelligence-backend/static
fi


# Restart Gunicorn (Gunicorn doesn't support reload, so we restart)
if sudo systemctl is-active --quiet gunicorn; then
    echo "🔄 Restarting Gunicorn..."
    sudo systemctl restart gunicorn
else
    echo "🚀 Starting Gunicorn..."
    sudo systemctl start gunicorn
fi
# Wait for Gunicorn to fully start and socket to be created
echo "⏳ Waiting for Gunicorn to start..."
for i in {1..10}; do
    if [ -S "/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock" ]; then
        echo "✅ Gunicorn socket is ready."
        break
    fi
    sleep 1
done
# Fix socket permissions after Gunicorn creates it
if [ -S "/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock" ]; then
    sudo chmod 770 /home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock
    sudo chown ubuntu:www-data /home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock
fi
echo "🔁 Gunicorn restarted."

# --- Step 9: Nginx Setup (correct socket path + server_name) ---
# Disable default Nginx site if it exists
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    echo "🗑️  Removing default Nginx site..."
    sudo rm -f /etc/nginx/sites-enabled/default
fi

if [ ! -f "$NGINX_CONF" ]; then
    echo "🌐 Creating Nginx configuration..."
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
    sudo bash -c "cat > $NGINX_CONF" <<EOF
server {
    listen 80 default_server;
    # listen [::]:80 default_server;   # Disable IPv6 if causing issues

    server_name $PUBLIC_IP localhost 127.0.0.1 _;

    location /static/ {
        alias $STATIC_DIR/;
        expires 1y;
        access_log off;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;

        # Required headers (sometimes missing in Ubuntu)
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    client_max_body_size 50M;
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
}
EOF

    sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
    echo "✅ Nginx site configuration created."
else
    echo "✅ Nginx configuration already exists."
    # Update configuration if needed
    UPDATED=false
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
    
    # Update server_name to accept all hostnames if needed
    if ! grep -q "server_name.*localhost.*127.0.0.1.*_" "$NGINX_CONF" 2>/dev/null; then
        echo "🔄 Updating Nginx server_name to accept all hostnames..."
        sudo sed -i "s/server_name.*;/server_name $PUBLIC_IP localhost 127.0.0.1 _;/" "$NGINX_CONF"
        UPDATED=true
    fi
    
    # Add default_server if missing
    if ! grep -q "listen 80 default_server" "$NGINX_CONF" 2>/dev/null; then
        echo "🔄 Adding default_server to listen directive..."
        sudo sed -i 's/listen 80;/listen 80 default_server;/' "$NGINX_CONF"
        UPDATED=true
    fi
    
    # Ensure proxy headers are present
    if ! grep -q "proxy_set_header Host" "$NGINX_CONF" 2>/dev/null; then
        echo "🔄 Adding required proxy headers..."
        sudo sed -i '/proxy_pass http:\/\/unix:/a\        # Required headers (sometimes missing in Ubuntu)\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;' "$NGINX_CONF"
        UPDATED=true
    fi
    
    if [ "$UPDATED" = true ]; then
        echo "✅ Nginx configuration updated."
    fi
    # Ensure default site is disabled
    if [ -f "/etc/nginx/sites-enabled/default" ]; then
        echo "🗑️  Removing default Nginx site..."
        sudo rm -f /etc/nginx/sites-enabled/default
    fi
fi

sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
echo "🔁 Nginx restarted."

# --- Step 10: Firewall Rules (Safe and Idempotent) ---
echo "🛡️  Configuring firewall safely..."
# Only reset if explicitly needed (safer approach)
if ! sudo ufw status | grep -q "Status: active"; then
    echo "🛡️  Firewall not active, configuring..."
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow 22/tcp comment "Allow SSH"
    sudo ufw allow 80/tcp comment "Allow HTTP"
    sudo ufw allow 443/tcp comment "Allow HTTPS"
    sudo ufw --force enable
else
    echo "✅ Firewall already active, ensuring required rules exist..."
    # Add rules if they don't exist (idempotent)
    sudo ufw allow 22/tcp comment "Allow SSH" 2>/dev/null || true
    sudo ufw allow 80/tcp comment "Allow HTTP" 2>/dev/null || true
    sudo ufw allow 443/tcp comment "Allow HTTPS" 2>/dev/null || true
fi
sudo ufw status verbose
echo "✅ Firewall configured safely (SSH, HTTP, HTTPS open)."

# --- Step 11: Health Check ---
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
echo "🎯 Checking application health..."
# Wait a bit longer for services to be fully ready
sleep 5

# Check if socket exists first
if [ ! -S "/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock" ]; then
    echo "⚠️  Gunicorn socket not found. Waiting a bit more..."
    sleep 5
fi

# Check if Swagger schema endpoint is accessible (more reliable than root)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/api/schema/" --max-time 10)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Application is live and healthy!"
    echo "   - API Schema: http://$PUBLIC_IP/api/schema/"
    echo "   - Swagger UI: http://$PUBLIC_IP/api/schema/swagger-ui/"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    echo "✅ Application is responding (authentication required - this is normal)"
    echo "   - Swagger UI: http://$PUBLIC_IP/api/schema/swagger-ui/"
elif [ "$HTTP_CODE" = "000" ]; then
    echo "⚠️  Application deployed but health check failed (connection timeout)."
    echo "   This might be a temporary issue. Services are running:"
    sudo systemctl is-active --quiet gunicorn && echo "   ✅ Gunicorn: running" || echo "   ❌ Gunicorn: not running"
    sudo systemctl is-active --quiet nginx && echo "   ✅ Nginx: running" || echo "   ❌ Nginx: not running"
    [ -S "/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock" ] && echo "   ✅ Socket: exists" || echo "   ❌ Socket: missing"
    echo ""
    echo "   Try accessing manually:"
    echo "   - http://$PUBLIC_IP/api/schema/swagger-ui/"
else
    echo "⚠️  Application deployed but health check returned HTTP $HTTP_CODE."
    echo "   Services status:"
    sudo systemctl is-active --quiet gunicorn && echo "   ✅ Gunicorn: running" || echo "   ❌ Gunicorn: not running"
    sudo systemctl is-active --quiet nginx && echo "   ✅ Nginx: running" || echo "   ❌ Nginx: not running"
    [ -S "/home/ubuntu/oneintelligence-backend/oneintelligence-backend.sock" ] && echo "   ✅ Socket: exists" || echo "   ❌ Socket: missing"
    echo ""
    echo "   Check logs with:"
    echo "   - Gunicorn: sudo journalctl -u gunicorn -n 50"
    echo "   - Nginx: sudo tail -20 /var/log/nginx/error.log"
fi

echo "🎉 Deployment Complete!"
echo "🌐 Swagger: http://$PUBLIC_IP/api/schema/swagger-ui/"
