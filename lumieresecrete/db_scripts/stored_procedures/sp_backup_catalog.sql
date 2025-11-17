CREATE OR REPLACE PROCEDURE sp_backup_catalog()
LANGUAGE plpgsql
AS $$
DECLARE
    backup_file TEXT;
BEGIN
    -- Define the backup file name with a timestamp
    backup_file := 'catalog_backup_' || to_char(NOW(), 'YYYYMMDD_HH24MISS') || '.sql';

    -- Execute the backup command
    EXECUTE format('COPY (SELECT * FROM Products) TO ''/path/to/backup/%s'' WITH (FORMAT CSV, HEADER)', backup_file);

    -- Log the backup operation
    INSERT INTO AuditLog (TableName, Operation, Datetime, UserID)
    VALUES ('Products', 'Backup', NOW(), NULL); -- Replace NULL with the actual UserID if needed

    RAISE NOTICE 'Backup completed successfully: %', backup_file;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Backup failed: %', SQLERRM;
END;
$$;