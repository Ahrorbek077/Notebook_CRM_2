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


class AnalyticsService:
    """
    "Analitika" sahifasi uchun — Dashboard'dan farqli o'laroq, bu yerda
    SOTUV (accrual — qachon sotilgan) va KASSA (cash — qachon pul kelgan/
    ketgan) ALOHIDA-ALOHIDA ko'rsatiladi, qarz holati va oddiy tildagi
    tushuntirish matni bilan birga.

    Muammo (foydalanuvchi tasviridan): "bu oy 150 mln sotilgan, lekin pul
    asosan keyingi oylarda keladi, shu bilan birga avvalgi oylarning puli
    bu oyga tushadi" — bu ikki narsani Dashboard'dagi yagona "foyda"
    ko'rsatkichi aralashtirib yuborgan edi. Analitika sahifasi buni ajratib
    tushuntiradi.
    """

    CACHE_TIMEOUT = 300

    @staticmethod
    def get_overview(business_id) -> dict:
        cache_key = f'analytics_overview_{business_id}'
        data = cache.get(cache_key)
        if data is not None:
            return data

        business_name = AnalyticsService._business_name(business_id)
        period   = AnalyticsService._current_month_period(business_id)
        debt     = AnalyticsService._debt_position(business_id)
        aging    = AnalyticsService._aging_buckets(business_id)
        trend    = AnalyticsService._six_month_trend(business_id)
        narrative = AnalyticsService._build_narrative(business_name, period, debt)

        data = {
            'narrative': narrative,
            'period': period,
            'debt_position': debt,
            'aging': aging,
            'trend': trend,
        }
        cache.set(cache_key, data, timeout=AnalyticsService.CACHE_TIMEOUT)
        return data

    # ── Yordamchi metodlar ───────────────────────────────────────────────────
    @staticmethod
    def _business_name(business_id) -> str:
        from notebook.business.models import Business
        biz = Business.objects.filter(id=business_id).first()
        return biz.name if biz else "Biznes"

    @staticmethod
    def _current_month_period(business_id) -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    COALESCE(total_sales,    0),
                    COALESCE(total_expense,  0),
                    COALESCE(total_payments, 0)
                FROM monthly_summary_mv
                WHERE business_id = %s AND month = date_trunc('month', CURRENT_DATE);
            """, [business_id])
            row = c.fetchone()

        sales_accrual = float(row[0]) if row else 0.0
        cogs          = float(row[1]) if row else 0.0
        cash_in       = float(row[2]) if row else 0.0

        from notebook.company.models import BranchPayment
        from django.db.models import Sum
        from django.utils import timezone
        now = timezone.now()
        cash_out = BranchPayment.objects.filter(
            branch__company__business_id=business_id,
            created_at__year=now.year, created_at__month=now.month,
        ).exclude(payment_type='discount').aggregate(
            total=Sum('amount')
        )['total'] or 0

        return {
            'sales_accrual':        sales_accrual,
            'gross_profit_accrual': sales_accrual - cogs,
            'cash_in':               cash_in,
            'cash_out_supplier':     float(cash_out),
            'net_cash_flow':         cash_in - float(cash_out),
            'collected_percent':     round(cash_in / sales_accrual * 100, 1) if sales_accrual else 0,
        }

    @staticmethod
    def _debt_position(business_id) -> dict:
        from notebook.clients.models import Client
        from notebook.company.models import Company
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        from decimal import Decimal

        receivables = Client.objects.filter(business_id=business_id).aggregate(
            total=Coalesce(Sum('total_debt'), Decimal('0'))
        )['total'] or 0
        payables = Company.objects.filter(business_id=business_id).aggregate(
            total=Coalesce(Sum('total_debt'), Decimal('0'))
        )['total'] or 0

        receivables, payables = float(receivables), float(payables)
        return {
            'receivables': receivables,
            'payables':    payables,
            'net':         receivables - payables,
        }

    @staticmethod
    def _aging_buckets(business_id) -> list:
        """Mijozning qarzi qancha vaqtdan beri "harakatsiz" turgani — TAXMINIY
        ko'rsatkich (oxirgi to'lovdan/yaratilgandan beri o'tgan kunlar asosida).
        Har bir sotuvni alohida kuzatib (FIFO) hisoblamaydi — shunchaki
        umumiy holatdan tezkor signal beradi."""
        from notebook.clients.models import Client
        from django.db.models import Max
        from django.utils import timezone

        now = timezone.now()
        buckets = {
            '0-30':  {'label': "0–30 kun",   'amount': 0.0, 'count': 0},
            '31-60': {'label': "31–60 kun",  'amount': 0.0, 'count': 0},
            '61-90': {'label': "61–90 kun",  'amount': 0.0, 'count': 0},
            '90+':   {'label': "90+ kun",    'amount': 0.0, 'count': 0},
        }

        clients = Client.objects.filter(business_id=business_id, total_debt__gt=0)\
                                 .annotate(last_payment=Max('payments__created_at'))\
                                 .only('id', 'total_debt', 'created_at')

        for cl in clients:
            ref = cl.last_payment or cl.created_at
            days = (now - ref).days
            if days <= 30:
                key = '0-30'
            elif days <= 60:
                key = '31-60'
            elif days <= 90:
                key = '61-90'
            else:
                key = '90+'
            buckets[key]['amount'] += float(cl.total_debt)
            buckets[key]['count']  += 1

        return list(buckets.values())

    @staticmethod
    def _six_month_trend(business_id) -> dict:
        with connection.cursor() as c:
            c.execute("""
                SELECT
                    TO_CHAR(month, 'MM-YYYY'),
                    COALESCE(total_sales,    0),
                    COALESCE(total_payments, 0)
                FROM monthly_summary_mv
                WHERE business_id = %s
                  AND month >= date_trunc('month', CURRENT_DATE) - INTERVAL '5 months'
                ORDER BY month ASC;
            """, [business_id])
            rows = c.fetchall()

        from notebook.company.models import BranchPayment
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth

        cash_out_rows = BranchPayment.objects.filter(
            branch__company__business_id=business_id,
        ).exclude(payment_type='discount').annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(total=Sum('amount')).order_by('month')
        cash_out_map = {r['month'].strftime('%m-%Y'): float(r['total']) for r in cash_out_rows}

        labels   = [r[0] for r in rows]
        sales    = [float(r[1]) for r in rows]
        cash_in  = [float(r[2]) for r in rows]
        cash_out = [cash_out_map.get(lbl, 0.0) for lbl in labels]

        return {
            'labels':   labels,
            'sales':    sales,
            'cash_in':  cash_in,
            'cash_out': cash_out,
        }

    @staticmethod
    def _fmt(n) -> str:
        return f"{n:,.0f}".replace(',', ' ')

    @staticmethod
    def _build_narrative(business_name, period, debt) -> str:
        fmt = AnalyticsService._fmt
        sales      = period['sales_accrual']
        cash_in    = period['cash_in']
        cash_out   = period['cash_out_supplier']
        pct        = period['collected_percent']
        receivables = debt['receivables']
        payables    = debt['payables']
        net         = debt['net']

        if sales == 0:
            return (f"Bu oy hali sotuv qilinmagan. Mijozlardan kutilayotgan qarz "
                    f"{fmt(receivables)} so'm, ta'minotchilarga qarzingiz {fmt(payables)} so'm.")

        parts = [
            f"Bu oy {fmt(sales)} so'mlik tovar sotildi.",
            f"Shundan {fmt(cash_in)} so'm ({pct:.0f}%) naqd/o'tkazma orqali qaytarib olindi, "
            f"qolgan {fmt(max(sales - cash_in, 0))} so'm mijozlarning qarziga yozildi va "
            f"odatdagidek kelgusi 1–3 oy ichida tushishi kutiladi.",
        ]
        if cash_out > 0:
            parts.append(f"Ta'minotchilarga bu oy {fmt(cash_out)} so'm to'landi.")
        if payables > 0:
            parts.append(f"Hozirda ta'minotchilarga jami qarzingiz — {fmt(payables)} so'm.")
        if net >= 0:
            parts.append(
                f"Mijozlardan kutilayotgan pul ({fmt(receivables)} so'm) ta'minotchiga "
                f"qarzdan {fmt(abs(net))} so'm ko'p — umumiy moliyaviy holat ijobiy."
            )
        else:
            parts.append(
                f"Diqqat: ta'minotchiga qarz ({fmt(payables)} so'm) mijozlardan "
                f"kutilayotgan summadan {fmt(abs(net))} so'm ko'p — pul oqimini ehtiyotkorlik bilan kuzating."
            )
        return " ".join(parts)
