# notebook/dashboard/migrations/0003_business_scoped_mvs.py
"""
Dashboard Materialized View'larini BIZNES bo'yicha ajratish.

Avval bu MV lar BARCHA bizneslarning sotuv/to'lovlarini bitta qatorga
yig'ib hisoblardi — ya'ni Aka va Uka bir xil Dashboard raqamlarini ko'rardi.

Endi har bir qator `business_id`ga ega — DashboardService endi
`WHERE business_id = %s` bilan filtrlay oladi.
"""
from django.db import migrations

DROP_ALL = """
DROP MATERIALIZED VIEW IF EXISTS yearly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS monthly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS dashboard_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS top_products_mv CASCADE;
"""

CREATE_DAILY = """
CREATE MATERIALIZED VIEW dashboard_summary_mv AS
WITH sales_data AS (
    SELECT
        DATE(s.created_at) AS date,
        s.business_id       AS business_id,
        SUM(si.price_at_sale      * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY DATE(s.created_at), s.business_id
),
payment_data AS (
    SELECT
        DATE(created_at) AS date,
        business_id       AS business_id,
        SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY DATE(created_at), business_id
)
SELECT
    COALESCE(s.date, p.date)               AS date,
    COALESCE(s.business_id, p.business_id) AS business_id,
    COALESCE(s.total_sales,    0)          AS total_sales,
    COALESCE(s.total_expense,  0)          AS total_expense,
    COALESCE(p.total_payments, 0)          AS total_payments,
    COALESCE(p.total_payments, 0) - COALESCE(s.total_expense,0) AS total_profit,
    COALESCE(s.total_sales, 0)   - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s
FULL OUTER JOIN payment_data p ON s.date = p.date AND s.business_id = p.business_id
ORDER BY date
WITH DATA;
"""
CREATE_DAILY_IDX = """
CREATE UNIQUE INDEX dashboard_summary_mv_biz_date_idx
    ON dashboard_summary_mv (business_id, date);
"""

CREATE_MONTHLY = """
CREATE MATERIALIZED VIEW monthly_summary_mv AS
WITH sales_data AS (
    SELECT
        DATE_TRUNC('month', s.created_at)::date AS month,
        s.business_id                            AS business_id,
        SUM(si.price_at_sale      * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY DATE_TRUNC('month', s.created_at), s.business_id
),
payment_data AS (
    SELECT
        DATE_TRUNC('month', created_at)::date AS month,
        business_id                            AS business_id,
        SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY DATE_TRUNC('month', created_at), business_id
)
SELECT
    COALESCE(s.month, p.month)             AS month,
    COALESCE(s.business_id, p.business_id) AS business_id,
    COALESCE(s.total_sales,    0)          AS total_sales,
    COALESCE(s.total_expense,  0)          AS total_expense,
    COALESCE(p.total_payments, 0)          AS total_payments,
    COALESCE(p.total_payments, 0) - COALESCE(s.total_expense,0) AS total_profit,
    COALESCE(s.total_sales, 0)   - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s
FULL OUTER JOIN payment_data p ON s.month = p.month AND s.business_id = p.business_id
ORDER BY month
WITH DATA;
"""
CREATE_MONTHLY_IDX = """
CREATE UNIQUE INDEX monthly_summary_mv_biz_month_idx
    ON monthly_summary_mv (business_id, month);
"""

CREATE_YEARLY = """
CREATE MATERIALIZED VIEW yearly_summary_mv AS
WITH sales_data AS (
    SELECT
        EXTRACT(YEAR FROM s.created_at)::int AS year,
        s.business_id                         AS business_id,
        SUM(si.price_at_sale      * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY EXTRACT(YEAR FROM s.created_at), s.business_id
),
payment_data AS (
    SELECT
        EXTRACT(YEAR FROM created_at)::int AS year,
        business_id                         AS business_id,
        SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY EXTRACT(YEAR FROM created_at), business_id
)
SELECT
    COALESCE(s.year, p.year)               AS year,
    COALESCE(s.business_id, p.business_id) AS business_id,
    COALESCE(s.total_sales,    0)          AS total_sales,
    COALESCE(s.total_expense,  0)          AS total_expense,
    COALESCE(p.total_payments, 0)          AS total_payments,
    COALESCE(p.total_payments, 0) - COALESCE(s.total_expense,0) AS total_profit,
    COALESCE(s.total_sales, 0)   - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s
FULL OUTER JOIN payment_data p ON s.year = p.year AND s.business_id = p.business_id
ORDER BY year
WITH DATA;
"""
CREATE_YEARLY_IDX = """
CREATE UNIQUE INDEX yearly_summary_mv_biz_year_idx
    ON yearly_summary_mv (business_id, year);
"""

CREATE_TOP_PRODUCTS = """
CREATE MATERIALIZED VIEW top_products_mv AS
SELECT
    p.id                                            AS product_id,
    p.business_id                                   AS business_id,
    p.name                                           AS product_name,
    COALESCE(c.name, 'Kategoriyasiz')                AS category_name,
    COALESCE(SUM(si.quantity - si.returned_quantity), 0) AS total_sold,
    COALESCE(SUM((si.quantity - si.returned_quantity) * si.price_at_sale), 0) AS total_revenue,
    COALESCE(SUM((si.quantity - si.returned_quantity) * (si.price_at_sale - si.cost_price_at_sale)), 0) AS total_profit
FROM catalog_product p
LEFT JOIN sales_saleitem si ON si.product_id = p.id
LEFT JOIN sales_sale s ON s.id = si.sale_id AND s.status = 'active'
LEFT JOIN catalog_category c ON c.id = p.category_id
GROUP BY p.id, p.business_id, p.name, c.name
WITH DATA;
"""
CREATE_TOP_PRODUCTS_IDX = """
CREATE UNIQUE INDEX top_products_mv_biz_product_idx
    ON top_products_mv (business_id, product_id);
"""

# ── Orqaga qaytarish: avvalgi (biznessiz) MV holatiga qaytaramiz ──────────────
REVERSE_DAILY = """
CREATE MATERIALIZED VIEW dashboard_summary_mv AS
WITH sales_data AS (
    SELECT DATE(s.created_at) AS date,
        SUM(si.price_at_sale * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active' GROUP BY DATE(s.created_at)
),
payment_data AS (
    SELECT DATE(created_at) AS date, SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment WHERE is_cancelled = FALSE GROUP BY DATE(created_at)
)
SELECT COALESCE(s.date, p.date) AS date,
    COALESCE(s.total_sales,0) AS total_sales, COALESCE(s.total_expense,0) AS total_expense,
    COALESCE(p.total_payments,0) AS total_payments,
    COALESCE(p.total_payments,0) - COALESCE(s.total_expense,0) AS total_profit,
    COALESCE(s.total_sales,0) - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s FULL OUTER JOIN payment_data p ON s.date = p.date ORDER BY date WITH DATA;
CREATE UNIQUE INDEX dashboard_summary_mv_date_idx ON dashboard_summary_mv (date);
"""

REVERSE_ALL = DROP_ALL + REVERSE_DAILY  # to'liq reverse kerak bo'lsa, qolganini qo'lda qarang


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_fix_profit_formula'),
        ('business',  '0003_backfill_more_models'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                DROP_ALL,
                CREATE_DAILY,   CREATE_DAILY_IDX,
                CREATE_MONTHLY, CREATE_MONTHLY_IDX,
                CREATE_YEARLY,  CREATE_YEARLY_IDX,
                CREATE_TOP_PRODUCTS, CREATE_TOP_PRODUCTS_IDX,
            ],
            reverse_sql=REVERSE_ALL,
        ),
    ]
