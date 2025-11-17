CREATE OR REPLACE PROCEDURE sp_update_stock(
    IN p_product_variant_id INT,
    IN p_quantity INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE ProductVariant
    SET Quantity = Quantity + p_quantity
    WHERE ProductVariantID = p_product_variant_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product variant with ID % not found', p_product_variant_id;
    END IF;

    INSERT INTO AuditLog (TableName, Operation, Datetime, OldValue, NewValue, Field, UserID)
    VALUES ('ProductVariant', 'UPDATE', NOW(), (SELECT Quantity FROM ProductVariant WHERE ProductVariantID = p_product_variant_id), 
            (SELECT Quantity + p_quantity FROM ProductVariant WHERE ProductVariantID = p_product_variant_id), 
            'Quantity', NULL);
END;
$$;