from django.db import migrations

SQL_UP = """
CREATE TABLE IF NOT EXISTS "ReviewModerationLog" (
    "LogID" SERIAL PRIMARY KEY,
    "ReviewID" bigint NOT NULL UNIQUE REFERENCES "ProductReviews" ("id") ON DELETE CASCADE,
    "Status" varchar(32) NOT NULL DEFAULT 'pending',
    "Notes" text,
    "CreatedAt" timestamptz NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION fn_order_line_total(p_quantity integer, p_price numeric)
RETURNS numeric
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_quantity IS NULL OR p_price IS NULL THEN
        RETURN 0;
    END IF;
    RETURN p_quantity * p_price;
END;
$$;

CREATE OR REPLACE FUNCTION fn_order_total_sum(p_order_id integer)
RETURNS numeric
LANGUAGE plpgsql
AS $$
DECLARE
    v_total numeric;
BEGIN
    SELECT COALESCE(SUM("Quantity" * "Price"), 0)
    INTO v_total
    FROM "OrderItems"
    WHERE "OrderID" = p_order_id;
    RETURN v_total;
END;
$$;

CREATE OR REPLACE FUNCTION fn_format_order_code(p_order_id integer)
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN 'LS-' || LPAD(p_order_id::text, 6, '0');
END;
$$;

CREATE OR REPLACE PROCEDURE sp_recalculate_order_total(p_order_id integer)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(p_order_id);
    UPDATE "Orders"
    SET "TotalAmount" = fn_order_total_sum(p_order_id)
    WHERE "OrderID" = p_order_id;
END;
$$;

CREATE OR REPLACE PROCEDURE sp_adjust_variant_stock(p_variant_id integer, p_delta integer)
LANGUAGE plpgsql
AS $$
DECLARE
    v_quantity integer;
BEGIN
    PERFORM pg_advisory_xact_lock(p_variant_id);
    SELECT COALESCE("Quantity", 0)
    INTO v_quantity
    FROM "ProductVariant"
    WHERE "ProductVariantID" = p_variant_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Вариант % не найден', p_variant_id
            USING ERRCODE = 'P0002';
    END IF;

    v_quantity := v_quantity + COALESCE(p_delta, 0);
    IF v_quantity < 0 THEN
        RAISE EXCEPTION 'Недостаточно остатка для варианта %', p_variant_id
            USING ERRCODE = 'P0001';
    END IF;

    UPDATE "ProductVariant"
    SET "Quantity" = v_quantity
    WHERE "ProductVariantID" = p_variant_id;
END;
$$;

CREATE OR REPLACE PROCEDURE sp_flag_review_for_moderation(p_review_id bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "ProductReviews"
    SET "is_public" = FALSE,
        "updated_at" = NOW()
    WHERE "id" = p_review_id;

    INSERT INTO "ReviewModerationLog" ("ReviewID", "Status", "Notes")
    VALUES (p_review_id, 'pending', 'Отзыв автоматически отправлен на модерацию')
    ON CONFLICT ("ReviewID") DO UPDATE
    SET "Status" = 'pending',
        "Notes" = EXCLUDED."Notes",
        "CreatedAt" = NOW();
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_orderitems_validate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW."Quantity" IS NULL OR NEW."Quantity" <= 0 THEN
        RAISE EXCEPTION 'Количество позиции заказа должно быть положительным';
    END IF;
    IF NEW."Price" IS NULL OR NEW."Price" < 0 THEN
        RAISE EXCEPTION 'Цена позиции заказа должна быть неотрицательной';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_orderitems_recalculate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id integer;
BEGIN
    v_order_id := COALESCE(NEW."OrderID", OLD."OrderID");
    IF v_order_id IS NOT NULL THEN
        CALL sp_recalculate_order_total(v_order_id);
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_productreviews_after()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    CALL sp_flag_review_for_moderation(NEW.id);
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_orderitems_validate ON "OrderItems";
DROP TRIGGER IF EXISTS trg_orderitems_recalculate ON "OrderItems";
DROP TRIGGER IF EXISTS trg_productreviews_after_insert ON "ProductReviews";

CREATE TRIGGER trg_orderitems_validate
BEFORE INSERT OR UPDATE ON "OrderItems"
FOR EACH ROW EXECUTE FUNCTION trg_fn_orderitems_validate();

CREATE TRIGGER trg_orderitems_recalculate
AFTER INSERT OR UPDATE OR DELETE ON "OrderItems"
FOR EACH ROW EXECUTE FUNCTION trg_fn_orderitems_recalculate();

CREATE TRIGGER trg_productreviews_after_insert
AFTER INSERT ON "ProductReviews"
FOR EACH ROW EXECUTE FUNCTION trg_fn_productreviews_after();
"""

SQL_DOWN = """
DROP TRIGGER IF EXISTS trg_productreviews_after_insert ON "ProductReviews";
DROP TRIGGER IF EXISTS trg_orderitems_recalculate ON "OrderItems";
DROP TRIGGER IF EXISTS trg_orderitems_validate ON "OrderItems";

DROP FUNCTION IF EXISTS trg_fn_productreviews_after() CASCADE;
DROP FUNCTION IF EXISTS trg_fn_orderitems_recalculate() CASCADE;
DROP FUNCTION IF EXISTS trg_fn_orderitems_validate() CASCADE;

DROP PROCEDURE IF EXISTS sp_flag_review_for_moderation(bigint);
DROP PROCEDURE IF EXISTS sp_adjust_variant_stock(integer, integer);
DROP PROCEDURE IF EXISTS sp_recalculate_order_total(integer);

DROP FUNCTION IF EXISTS fn_format_order_code(integer);
DROP FUNCTION IF EXISTS fn_order_total_sum(integer);
DROP FUNCTION IF EXISTS fn_order_line_total(integer, numeric);

DROP TABLE IF EXISTS "ReviewModerationLog";
"""


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_promocode_order_discount_amount_and_more'),
    ]

    operations = [
        migrations.RunSQL(SQL_UP, SQL_DOWN),
    ]

