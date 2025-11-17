CREATE OR REPLACE FUNCTION fn_calculate_total(order_id INT)
RETURNS DECIMAL AS $$
DECLARE
    total DECIMAL := 0;
BEGIN
    SELECT SUM(oi.Quantity * oi.Price) INTO total
    FROM OrderItems oi
    WHERE oi.OrderID = order_id;

    RETURN total;
END;
$$ LANGUAGE plpgsql;