CREATE OR REPLACE FUNCTION update_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO AuditLog (TableName, Operation, Datetime, OldValue, NewValue, Field, UserID)
    VALUES (TG_TABLE_NAME, TG_OP, NOW(), row_to_json(OLD), row_to_json(NEW), TG_ARGV[0], current_user_id());

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_audit_log
AFTER UPDATE ON Users
FOR EACH ROW
EXECUTE FUNCTION update_audit_log();