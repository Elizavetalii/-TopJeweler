CREATE OR REPLACE FUNCTION fn_order_after_insert()
RETURNS TRIGGER AS $$
BEGIN
    -- Здесь можно добавить логику, которая будет выполняться после вставки заказа
    -- Например, обновление статистики или уведомление о новом заказе

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_after_insert
AFTER INSERT ON Orders
FOR EACH ROW
EXECUTE FUNCTION fn_order_after_insert();