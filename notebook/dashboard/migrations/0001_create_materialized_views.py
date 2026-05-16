"""
Migration: Barcha Materialized View larni yaratish
nootbookk/dashboard/migrations/0001_create_materialized_views.py
"""
from django.db import migrations


# ── SQL: DROP ────────────────────────────────────────────────────────────────

DROP_SQL = """
DROP MATERIALIZED VIEW IF EXISTS yearly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS monthly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS top_products_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS dashboard_summary_mv CASCADE;
"""

# ── SQL: CREATE Daily ────────────────────────────────────────────────────────

CREATE_DAILY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_summary_mv AS
WITH sales_data AS (
    SELECT
        DATE(s.created_at) AS date,

        SUM(
            si.price_at_sale *
            (si.quantity - si.returned_quantity)
        ) AS total_sales,

        SUM(
            si.cost_price_at_sale *
            (si.quantity - si.returned_quantity)
        ) AS total_expense

    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY DATE(s.created_at)
),

payment_data AS (
    SELECT
        DATE(created_at) AS date,

        SUM(
            amount - refunded_amount
        ) AS total_payments

    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY DATE(created_at)
)

SELECT
    COALESCE(s.date, p.date)                AS date,
    COALESCE(s.total_sales,    0)           AS total_sales,
    COALESCE(s.total_expense,  0)           AS total_expense,
    COALESCE(p.total_payments, 0)           AS total_payments,
    -- Real naqd foyda: client to'lovidan harajat ayiriladi
    COALESCE(p.total_payments, 0)
        - COALESCE(s.total_expense, 0)      AS total_profit,
    -- Potensial foyda: sotuv narxidan harajat (qarz ham kiritilgan)
    COALESCE(s.total_sales, 0)
        - COALESCE(s.total_expense, 0)      AS gross_profit

FROM sales_data s
FULL OUTER JOIN payment_data p ON s.date = p.date
ORDER BY date
WITH DATA;
"""

CREATE_DAILY_INDEX = """
CREATE UNIQUE INDEX dashboard_summary_mv_date_idx
    ON dashboard_summary_mv (date);
"""

# ── SQL: CREATE Monthly ──────────────────────────────────────────────────────

CREATE_MONTHLY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_summary_mv AS
WITH sales_data AS (
    SELECT
        DATE_TRUNC('month', s.created_at)::date AS month,

        SUM(
            si.price_at_sale *
            (si.quantity - si.returned_quantity)
        ) AS total_sales,

        SUM(
            si.cost_price_at_sale *
            (si.quantity - si.returned_quantity)
        ) AS total_expense

    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY DATE_TRUNC('month', s.created_at)
),

payment_data AS (
    SELECT
        DATE_TRUNC('month', created_at)::date AS month,

        SUM(
            amount - refunded_amount
        ) AS total_payments

    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY DATE_TRUNC('month', created_at)
)

SELECT
    COALESCE(s.month, p.month)              AS month,
    COALESCE(s.total_sales,    0)           AS total_sales,
    COALESCE(s.total_expense,  0)           AS total_expense,
    COALESCE(p.total_payments, 0)           AS total_payments,
    COALESCE(p.total_payments, 0)
        - COALESCE(s.total_expense, 0)      AS total_profit,
    COALESCE(s.total_sales, 0)
        - COALESCE(s.total_expense, 0)      AS gross_profit

FROM sales_data s
FULL OUTER JOIN payment_data p ON s.month = p.month
ORDER BY month
WITH DATA;
"""

CREATE_MONTHLY_INDEX = """
CREATE UNIQUE INDEX monthly_summary_mv_month_idx
    ON monthly_summary_mv (month);
"""

# ── SQL: CREATE Yearly ───────────────────────────────────────────────────────

CREATE_YEARLY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS yearly_summary_mv AS
WITH sales_data AS (
    SELECT
        EXTRACT(YEAR FROM s.created_at)::int AS year,

        SUM(
            si.price_at_sale *
            (si.quantity - si.returned_quantity)
        ) AS total_sales,

        SUM(
            si.cost_price_at_sale *
            (si.quantity - si.returned_quantity)
        ) AS total_expense

    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY EXTRACT(YEAR FROM s.created_at)
),

payment_data AS (
    SELECT
        EXTRACT(YEAR FROM created_at)::int AS year,

        SUM(
            amount - refunded_amount
        ) AS total_payments

    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY EXTRACT(YEAR FROM created_at)
)

SELECT
    COALESCE(s.year, p.year)                AS year,
    COALESCE(s.total_sales,    0)           AS total_sales,
    COALESCE(s.total_expense,  0)           AS total_expense,
    COALESCE(p.total_payments, 0)           AS total_payments,
    COALESCE(p.total_payments, 0)
        - COALESCE(s.total_expense, 0)      AS total_profit,
    COALESCE(s.total_sales, 0)
        - COALESCE(s.total_expense, 0)      AS gross_profit

FROM sales_data s
FULL OUTER JOIN payment_data p ON s.year = p.year
ORDER BY year
WITH DATA;
"""

CREATE_YEARLY_INDEX = """
CREATE UNIQUE INDEX yearly_summary_mv_year_idx
    ON yearly_summary_mv (year);
"""

# ── SQL: CREATE Top Products ─────────────────────────────────────────────────

CREATE_TOP_PRODUCTS = """
CREATE MATERIALIZED VIEW IF NOT EXISTS top_products_mv AS
SELECT
    p.id                                            AS product_id,
    p.name                                          AS product_name,
    COALESCE(c.name, 'Kategoriyasiz')               AS category_name,

    COALESCE(
        SUM(si.quantity - si.returned_quantity),
        0
    ) AS total_sold,

    COALESCE(
        SUM(
            (si.quantity - si.returned_quantity)
            * si.price_at_sale
        ),
        0
    ) AS total_revenue,

    COALESCE(
        SUM(
            (si.quantity - si.returned_quantity)
            * (si.price_at_sale - si.cost_price_at_sale)
        ),
        0
    ) AS total_profit

FROM catalog_product p
LEFT JOIN sales_saleitem si ON si.product_id = p.id
LEFT JOIN sales_sale s
    ON s.id = si.sale_id
    AND s.status = 'active'
LEFT JOIN catalog_category c ON c.id = p.category_id

GROUP BY p.id, p.name, c.name
WITH DATA;
"""

CREATE_TOP_PRODUCTS_INDEX = """
CREATE UNIQUE INDEX top_products_mv_product_id_idx
    ON top_products_mv (product_id);
"""


# ── Migration ────────────────────────────────────────────────────────────────

class Migration(migrations.Migration):

    dependencies = [
        ('sales',     '__first__'),
        ('payments',  '__first__'),
        ('catalog',   '__first__'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                CREATE_DAILY,
                CREATE_DAILY_INDEX,

                CREATE_MONTHLY,
                CREATE_MONTHLY_INDEX,

                CREATE_YEARLY,
                CREATE_YEARLY_INDEX,

                CREATE_TOP_PRODUCTS,
                CREATE_TOP_PRODUCTS_INDEX,
            ],
            reverse_sql=DROP_SQL,
        ),
    ]
