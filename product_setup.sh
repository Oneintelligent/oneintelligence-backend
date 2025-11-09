#!/bin/bash
set -e

# -------------------------------
# PostgreSQL Setup Script for OneIntelligence Backend
# -------------------------------

# --- Configuration ---
DB_NAME="oneintelligence-db"
DB_USER="oneintelligence"
DB_PASS="Onei@123"

echo "🚀 Starting PostgreSQL setup..."

# --- Step 0: Update system ---
sudo apt update -y && sudo apt upgrade -y

# --- Step 1: Install PostgreSQL ---
sudo apt install -y postgresql postgresql-contrib

# --- Step 2: Start & enable PostgreSQL ---
sudo systemctl enable postgresql
sudo systemctl start postgresql

# --- Step 3: Create DB user if missing ---
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    echo "✅ PostgreSQL user $DB_USER created."
else
    echo "✅ PostgreSQL user $DB_USER exists."
fi

# --- Step 4: Create DB if missing ---
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres createdb "$DB_NAME" -O "$DB_USER"
    echo "✅ Database $DB_NAME created."
else
    echo "✅ Database $DB_NAME exists."
fi

# --- Step 5: Configure role defaults ---
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
echo "✅ PostgreSQL role configuration applied."

echo "🎉 PostgreSQL setup complete!"
