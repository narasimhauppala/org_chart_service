#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready
# Use environment variables for connection details if possible
DB_HOST="${DB_HOST:-db}" # Default to service name 'db'
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-user}"
DB_NAME="${POSTGRES_DB:-orgchart_db}"

# Check if pg_isready is available
if ! command -v pg_isready &> /dev/null
then
    echo "pg_isready command could not be found. Trying netcat..."
    # Fallback using netcat if pg_isready is not installed (might require installing netcat in Dockerfile)
    # Ensure netcat is installed: RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*
    while ! nc -z $DB_HOST $DB_PORT; do
      echo "Waiting for PostgreSQL ($DB_HOST:$DB_PORT)..."
      sleep 2
    done
else
    echo "Waiting for PostgreSQL ($DB_HOST:$DB_PORT) with user $DB_USER on db $DB_NAME..."
    until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -q; do
      echo "PostgreSQL is unavailable - sleeping"
      sleep 2
    done
fi

echo "PostgreSQL started"

# Run Alembic migrations
# Make sure alembic is installed in the virtual environment/container
echo "Running database migrations..."
alembic upgrade head

echo "Migrations complete."

# Execute the main container command 
echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
