#!/bin/bash

# Restore the database from the latest backup

# Load environment variables
source .env

# Define backup directory and latest backup file
BACKUP_DIR="./backups"
LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.sql | head -n 1)

# Check if the latest backup file exists
if [ -f "$LATEST_BACKUP" ]; then
    echo "Restoring database from $LATEST_BACKUP..."
    
    # Restore the database
    psql -U $DB_USER -d $DB_NAME -f "$LATEST_BACKUP"
    
    if [ $? -eq 0 ]; then
        echo "Database restored successfully."
    else
        echo "Error occurred during database restoration."
    fi
else
    echo "No backup files found in $BACKUP_DIR."
fi