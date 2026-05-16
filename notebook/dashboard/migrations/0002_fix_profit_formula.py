"""
Migration: MV da foyda formulasini to'g'irlash
  Eski: total_profit = total_sales - total_expense  (potensial foyda)
  Yangi: total_profit = total_payments - total_expense (real naqd foyda)
         gross_profit = total_sales - total_expense   (yangi ustun - qarz bilan)
"""
from django.db import migrations

DROP_OLD = """
DROP MATERIALIZED VIEW IF EXISTS yearly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS monthly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS dashboard_summary_mv CASCADE;
"""

CREATE_DAILY = """
CREATE MATERIALIZED VIEW dashboard_summary_mv AS
WITH sales_data AS (
    SELECT
        DATE(s.created_at) AS date,
        SUM(si.price_at_sale      * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY DATE(s.created_at)
),
payment_data AS (
    SELECT
        DATE(created_at) AS date,
        SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY DATE(created_at)
)
SELECT
    COALESCE(s.date, p.date)                                    AS date,
    COALESCE(s.total_sales,    0)                               AS total_sales,
    COALESCE(s.total_expense,  0)                               AS total_expense,
    COALESCE(p.total_payments, 0)                               AS total_payments,
    -- Real foyda: naqd kelgan pul - xarid xarajati
    COALESCE(p.total_payments, 0) - COALESCE(s.total_expense,0) AS total_profit,
    -- Potensial foyda: sotuv narxi - xarid xarajati (qarz ham kiritilgan)
    COALESCE(s.total_sales, 0)   - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s
FULL OUTER JOIN payment_data p ON s.date = p.date
ORDER BY date
WITH DATA;
"""

CREATE_DAILY_IDX = """
CREATE UNIQUE INDEX dashboard_summary_mv_date_idx ON dashboard_summary_mv (date);
"""

CREATE_MONTHLY = """
CREATE MATERIALIZED VIEW monthly_summary_mv AS
WITH sales_data AS (
    SELECT
        DATE_TRUNC('month', s.created_at)::date AS month,
        SUM(si.price_at_sale      * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY DATE_TRUNC('month', s.created_at)
),
payment_data AS (
    SELECT
        DATE_TRUNC('month', created_at)::date AS month,
        SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY DATE_TRUNC('month', created_at)
)
SELECT
    COALESCE(s.month, p.month)                                  AS month,
    COALESCE(s.total_sales,    0)                               AS total_sales,
    COALESCE(s.total_expense,  0)                               AS total_expense,
    COALESCE(p.total_payments, 0)                               AS total_payments,
    COALESCE(p.total_payments, 0) - COALESCE(s.total_expense,0) AS total_profit,
    COALESCE(s.total_sales, 0)   - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s
FULL OUTER JOIN payment_data p ON s.month = p.month
ORDER BY month
WITH DATA;
"""

CREATE_MONTHLY_IDX = """
CREATE UNIQUE INDEX monthly_summary_mv_month_idx ON monthly_summary_mv (month);
"""

CREATE_YEARLY = """
CREATE MATERIALIZED VIEW yearly_summary_mv AS
WITH sales_data AS (
    SELECT
        EXTRACT(YEAR FROM s.created_at)::int AS year,
        SUM(si.price_at_sale      * (si.quantity - si.returned_quantity)) AS total_sales,
        SUM(si.cost_price_at_sale * (si.quantity - si.returned_quantity)) AS total_expense
    FROM sales_sale s
    JOIN sales_saleitem si ON si.sale_id = s.id
    WHERE s.status = 'active'
    GROUP BY EXTRACT(YEAR FROM s.created_at)
),
payment_data AS (
    SELECT
        EXTRACT(YEAR FROM created_at)::int AS year,
        SUM(amount - refunded_amount) AS total_payments
    FROM payments_payment
    WHERE is_cancelled = FALSE
    GROUP BY EXTRACT(YEAR FROM created_at)
)
SELECT
    COALESCE(s.year, p.year)                                    AS year,
    COALESCE(s.total_sales,    0)                               AS total_sales,
    COALESCE(s.total_expense,  0)                               AS total_expense,
    COALESCE(p.total_payments, 0)                               AS total_payments,
    COALESCE(p.total_payments, 0) - COALESCE(s.total_expense,0) AS total_profit,
    COALESCE(s.total_sales, 0)   - COALESCE(s.total_expense,0) AS gross_profit
FROM sales_data s
FULL OUTER JOIN payment_data p ON s.year = p.year
ORDER BY year
WITH DATA;
"""

CREATE_YEARLY_IDX = """
CREATE UNIQUE INDEX yearly_summary_mv_year_idx ON yearly_summary_mv (year);
"""

REVERSE = """
DROP MATERIALIZED VIEW IF EXISTS yearly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS monthly_summary_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS dashboard_summary_mv CASCADE;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0001_create_materialized_views'),
    ]
    operations = [
        migrations.RunSQL(
            sql=[
                DROP_OLD,
                CREATE_DAILY, CREATE_DAILY_IDX,
                CREATE_MONTHLY, CREATE_MONTHLY_IDX,
                CREATE_YEARLY, CREATE_YEARLY_IDX,
            ],
            reverse_sql=REVERSE,
        ),
    ]
