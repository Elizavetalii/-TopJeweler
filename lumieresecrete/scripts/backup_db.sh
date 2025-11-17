#!/bin/bash

# Backup database script for Lumieresecrete project

# Load environment variables
source .env

# Define backup file name with timestamp
BACKUP_FILE="backups/db_backup_$(date +'%Y%m%d_%H%M%S').sql"

# Execute the database backup command
pg_dump -U $DB_USER -h $DB_HOST -p $DB_PORT $DB_NAME > $BACKUP_FILE

# Check if the backup was successful
if [ $? -eq 0 ]; then
  echo "Database backup successful: $BACKUP_FILE"
else
  echo "Database backup failed"
  exit 1
fi