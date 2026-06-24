# notebook/dashboard/services.py
"""
DashboardService — Materialized View lar asosida statistika.

ENDI HAR BIR METOD business_id BILAN ISHLAYDI — har biznes faqat
o'zining sotuv/to'lov/mahsulot raqamlarini ko'radi.

Hisob mantigi:
  total_sales   = Sotilgan narx × (qty - returned_qty)  [sotuv narxi]
  total_expense = Tan narx     × (qty - returned_qty)  [cost_price_at_sale]
  total_profit  = total_payments - total_expense        [real naqd foyda]
  gross_profit  = total_sales - total_expense           [potensial foyda (qarz+naqd)]
"""
from django.db import connection
from django.core.cache import cache


class DashboardService:

    CACHE_TIMEOUT = 300  # 5 daqiqa

    @staticmethod
    def get_dashboard_data(business_id) -> dict:
        cache_key = f'dashboard_full_data_{business_id}'
        data = cache.get(cache_key)
        if data is None:
            data = {
                'today':  DashboardService._period_stats(business_id, 'today'),
                'week':   DashboardService._period_stats(business_id, 'week'),
                'month':  DashboardService._period_stats(business_id, 'month'),
                'year':   DashboardService._period_stats(business_id, 'year'),
                'chart': {
                    'weekly':  DashboardService._weekly_chart(business_id),
                    'monthly': DashboardService._monthly_chart(business_id),
                    'yearly':  DashboardService._yearly_chart(business_id),
                },
                'top_products': DashboardService._top_products(business_id),
            }
            cache.set(cache_key, data, timeout=DashboardService.CACHE_TIMEOUT)
        return data

    # ── Period stats (today / week / month / year) ─────────────────────────
    @staticmethod
    def _period_stats(business_id, period: str) -> dict:
        period_sql = {
            'today': "date = CURRENT_DATE",
            'week':  "date >= date_trunc('week', CURRENT_DATE)",
            'month': "date >= date_trunc('month', CURRENT_DATE)",
            'year':  "date >= date_trunc('year', CURRENT_DATE)",
        }
        where = period_sql.get(period, "date = CURRENT_DATE")

        with connection.cursor() as c:
            c.execute(f"""
                SELECT
                    COALESCE(SUM(total_sales),    0),
                    COALESCE(SUM(total_expense),  0),
                    COALESCE(SUM(total_payments), 0),
                    COALESCE(SUM(total_profit),   0),
                    COALESCE(SUM(gross_profit),   0)
                FROM dashboard_summary_mv
                WHERE business_id = %s AND {where};
            """, [business_id])
            row = c.fetchone()

        if not row or row[0] is None:
            return {'sale': 0, 'expense': 0, 'payment': 0,
                    'profit': 0, 'gross_profit': 0}
        return {
            'sale':         float(row[0]),
            'expense':      float(row[1]),
            'payment':      float(row[2]),
            'profit':       float(row[3]),
            'gross_profit': float(row[4]),
        }

    # ── Charts ──────────────────────────────────────────────────────────────
    @staticmethod
    def _weekly_chart(business_id) -> dict:
        """So'nggi 7 kun — kunlik grafik."""
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    TO_CHAR(date, 'DD-MM'),
                    COALESCE(total_sales,    0),
                    COALESCE(total_expense,  0),
                    COALESCE(total_payments, 0),
                    COALESCE(total_profit,   0)
                FROM dashboard_summary_mv
                WHERE business_id = %s AND date >= CURRENT_DATE - INTERVAL '6 days'
                ORDER BY date ASC;
            """, [business_id])
            rows = c.fetchall()
        return {
            'labels':   [r[0] for r in rows],
            'sales':    [float(r[1]) for r in rows],
            'expenses': [float(r[2]) for r in rows],
            'payments': [float(r[3]) for r in rows],
            'profits':  [float(r[4]) for r in rows],
        }

    @staticmethod
    def _monthly_chart(business_id) -> dict:
        """Joriy yil oylik grafik."""
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    TO_CHAR(month, 'MM-YYYY'),
                    COALESCE(total_sales,    0),
                    COALESCE(total_expense,  0),
                    COALESCE(total_payments, 0),
                    COALESCE(total_profit,   0)
                FROM monthly_summary_mv
                WHERE business_id = %s AND month >= date_trunc('year', CURRENT_DATE)
                ORDER BY month ASC;
            """, [business_id])
            rows = c.fetchall()
        return {
            'labels':   [r[0] for r in rows],
            'sales':    [float(r[1]) for r in rows],
            'expenses': [float(r[2]) for r in rows],
            'payments': [float(r[3]) for r in rows],
            'profits':  [float(r[4]) for r in rows],
        }

    @staticmethod
    def _yearly_chart(business_id) -> dict:
        """Barcha yillar grafigi."""
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    year,
                    COALESCE(total_sales,    0),
                    COALESCE(total_expense,  0),
                    COALESCE(total_payments, 0),
                    COALESCE(total_profit,   0)
                FROM yearly_summary_mv
                WHERE business_id = %s
                ORDER BY year ASC;
            """, [business_id])
            rows = c.fetchall()
        return {
            'labels':   [str(r[0]) for r in rows],
            'sales':    [float(r[1]) for r in rows],
            'expenses': [float(r[2]) for r in rows],
            'payments': [float(r[3]) for r in rows],
            'profits':  [float(r[4]) for r in rows],
        }

    # ── Top Products ────────────────────────────────────────────────────────
    @staticmethod
    def _top_products(business_id, limit: int = 10) -> list:
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    product_name,
                    category_name,
                    total_sold,
                    COALESCE(total_revenue, 0),
                    COALESCE(total_profit,  0)
                FROM top_products_mv
                WHERE business_id = %s AND total_sold > 0
                ORDER BY total_sold DESC
                LIMIT %s;
            """, [business_id, limit])
            rows = c.fetchall()
        return [
            {
                'name':     r[0],
                'category': r[1],
                'sold':     int(r[2]),
                'revenue':  float(r[3]),
                'profit':   float(r[4]),
            }
            for r in rows
        ]
