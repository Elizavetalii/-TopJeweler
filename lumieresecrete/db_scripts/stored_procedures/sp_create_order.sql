CREATE OR REPLACE FUNCTION sp_create_order(
    p_user_id INT,
    p_store_id INT,
    p_total_amount DECIMAL(10,2),
    p_status_id INT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO Orders (UserID, StoreID, CreatedAt, StatusID, TotalAmount)
    VALUES (p_user_id, p_store_id, NOW(), p_status_id, p_total_amount);
    
    -- Optionally, you can add logic to handle order items here
    -- For example, you might want to insert into OrderItems based on a cart or similar logic

    -- Log the action in the AuditLog
    INSERT INTO AuditLog (TableName, Operation, Datetime, UserID)
    VALUES ('Orders', 'INSERT', NOW(), p_user_id);
END;
$$ LANGUAGE plpgsql;