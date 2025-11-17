from django.db import migrations


SQL_CREATE = """
CREATE OR REPLACE VIEW "vw_order_summary" AS
SELECT
    o."OrderID" AS order_id,
    o."UserID" AS user_id,
    u."username" AS user_name,
    o."CreatedAt" AS created_at,
    COALESCE(o."TotalAmount", 0) AS total_amount,
    s."NameStatus" AS status_name,
    st."StoreID" AS store_id,
    st."Name" AS store_name
FROM "Orders" o
LEFT JOIN "Users" u ON o."UserID" = u."id"
LEFT JOIN "Status" s ON o."StatusID" = s."StatusID"
LEFT JOIN "Stores" st ON o."StoreID" = st."StoreID";

CREATE OR REPLACE VIEW "vw_product_performance" AS
SELECT
    p."ProductID" AS product_id,
    p."Name" AS product_name,
    c."Name" AS category_name,
    COALESCE(SUM(oi."Quantity"), 0) AS total_quantity,
    COALESCE(SUM(oi."Quantity" * oi."Price"), 0) AS total_revenue
FROM "Products" p
LEFT JOIN "Categories" c ON p."CategoryID" = c."CategoryID"
LEFT JOIN "ProductVariant" pv ON pv."ProductID" = p."ProductID"
LEFT JOIN "OrderItems" oi ON oi."ProductVariantID" = pv."ProductVariantID"
GROUP BY p."ProductID", p."Name", c."Name";

CREATE OR REPLACE VIEW "vw_user_activity" AS
SELECT
    u."id" AS user_id,
    u."username" AS username,
    u."email" AS email,
    COALESCE(COUNT(DISTINCT o."OrderID"), 0) AS orders_count,
    COALESCE(SUM(o."TotalAmount"), 0) AS orders_total,
    COALESCE(MAX(o."CreatedAt"), NULL) AS last_order_date,
    COALESCE(MAX(sl."LoginTime"), NULL) AS last_login
FROM "Users" u
LEFT JOIN "Orders" o ON o."UserID" = u."id"
LEFT JOIN "SessionLog" sl ON sl."UserID" = u."id"
GROUP BY u."id", u."username", u."email";
"""

SQL_DROP = """
DROP VIEW IF EXISTS "vw_user_activity";
DROP VIEW IF EXISTS "vw_product_performance";
DROP VIEW IF EXISTS "vw_order_summary";
"""


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(SQL_CREATE, SQL_DROP),
    ]

