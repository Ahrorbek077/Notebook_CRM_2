# notebook/dashboard/services.py
from django.db import connection
from django.core.cache import cache


class DashboardService:

    @staticmethod
    def get_dashboard_data() -> dict:
        cache_key = 'dashboard_full_data'
        data = cache.get(cache_key)
        if data is None:
            data = {
                'year':  DashboardService._year_stats(),
                'today': DashboardService._today_stats(),
                'chart': {
                    'weekly':  DashboardService._weekly_chart(),
                    'monthly': DashboardService._monthly_chart(),
                    'yearly':  DashboardService._yearly_chart(),
                },
                'top_products': DashboardService._top_products(),
            }
            cache.set(cache_key, data, timeout=300)
        return data

    @staticmethod
    def _year_stats() -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT COALESCE(SUM(total_sales),0),
                       COALESCE(SUM(total_expense),0),
                       COALESCE(SUM(total_payments),0),
                       COALESCE(SUM(total_profit),0),
                       COALESCE(SUM(gross_profit),0)
                FROM dashboard_summary_mv
                WHERE date >= date_trunc('year', CURRENT_DATE);
            """)
            row = c.fetchone()
        return {
            'sale':         float(row[0]),   # Umumiy sotuv (qarz+naqd)
            'expense':      float(row[1]),   # Harajat (xarid tan narxi)
            'payment':      float(row[2]),   # Naqd kelgan to'lov
            'profit':       float(row[3]),   # Real naqd foyda (payment-expense)
            'gross_profit': float(row[4]),   # Potensial foyda (sale-expense)
        }

    @staticmethod
    def _weekly_chart() -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT TO_CHAR(date,'DD-MM'),
                       total_sales, total_expense, total_payments, total_profit
                FROM dashboard_summary_mv
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY date ASC;
            """)
            rows = c.fetchall()
        return {
            'labels':   [r[0] for r in rows],
            'sales':    [float(r[1]) for r in rows],
            'expenses': [float(r[2]) for r in rows],
            'payments': [float(r[3]) for r in rows],
            'profits':  [float(r[4]) for r in rows],
        }

    @staticmethod
    def _monthly_chart() -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT TO_CHAR(month,'MM-YYYY'),
                       total_sales, total_expense, total_payments, total_profit
                FROM monthly_summary_mv
                WHERE month >= date_trunc('year', CURRENT_DATE)
                ORDER BY month ASC;
            """)
            rows = c.fetchall()
        return {
            'labels':   [r[0] for r in rows],
            'sales':    [float(r[1]) for r in rows],
            'expenses': [float(r[2]) for r in rows],
            'payments': [float(r[3]) for r in rows],
            'profits':  [float(r[4]) for r in rows],
        }

    @staticmethod
    def _yearly_chart() -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT year, total_sales, total_expense, total_payments, total_profit
                FROM yearly_summary_mv
                ORDER BY year ASC;
            """)
            rows = c.fetchall()
        return {
            'labels':   [str(r[0]) for r in rows],
            'sales':    [float(r[1]) for r in rows],
            'expenses': [float(r[2]) for r in rows],
            'payments': [float(r[3]) for r in rows],
            'profits':  [float(r[4]) for r in rows],
        }

    @staticmethod
    def _today_stats() -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    COALESCE(total_sales,    0),
                    COALESCE(total_expense,  0),
                    COALESCE(total_payments, 0),
                    COALESCE(total_profit,   0),
                    COALESCE(gross_profit,   0)
                FROM dashboard_summary_mv
                WHERE date = CURRENT_DATE;
            """)
            row = c.fetchone()
        if not row:
            return {'sale': 0, 'expense': 0, 'payment': 0, 'profit': 0, 'gross_profit': 0}
        return {
            'sale':         float(row[0]),
            'expense':      float(row[1]),
            'payment':      float(row[2]),
            'profit':       float(row[3]),
            'gross_profit': float(row[4]),
        }

    @staticmethod
    def _top_products() -> list:
        with connection.cursor() as c:
            c.execute("""
                SELECT product_name, category_name, total_sold, total_revenue, total_profit
                FROM top_products_mv
                ORDER BY total_sold DESC
                LIMIT 10;
            """)
            rows = c.fetchall()
        return [
            {'name': r[0], 'category': r[1], 'sold': r[2],
             'revenue': float(r[3]), 'profit': float(r[4])}
            for r in rows
        ]
