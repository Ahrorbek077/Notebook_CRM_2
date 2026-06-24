# notebook/dashboard/tasks.py
from celery import shared_task
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

MATERIALIZED_VIEWS = [
    'dashboard_summary_mv',
    'top_products_mv',
    'monthly_summary_mv',
    'yearly_summary_mv',
]


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    max_retries=3,
    name='dashboard.refresh_materialized_views',
)
def refresh_materialized_views(self):
    """Barcha MV larni CONCURRENTLY yangilash."""
    errors = []
    with connection.cursor() as cursor:
        for view in MATERIALIZED_VIEWS:
            try:
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view};")
                logger.info("✅ %s yangilandi", view)
            except Exception as exc:
                logger.error("❌ %s xatolik: %s", view, exc)
                errors.append(f"{view}: {exc}")
    if errors:
        raise RuntimeError("MV refresh xatoliklari:\n" + "\n".join(errors))

    # Cache ni tozalaymiz — har bir biznes uchun alohida key (yangi ma'lumotlar yuklansin)
    _clear_dashboard_cache()
    return "OK"


def _clear_dashboard_cache():
    from notebook.business.models import Business
    for biz_id in Business.objects.values_list('id', flat=True):
        cache.delete(f'dashboard_full_data_{biz_id}')


def refresh_mv_sync():
    """
    Celery ishlamayotganda (development) sinxron refresh.
    Sotuv/to'lovdan keyin chaqiriladi.
    """
    try:
        with connection.cursor() as cursor:
            for view in MATERIALIZED_VIEWS:
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view};")
        cache.delete('dashboard_full_data')  # eski kalit (mavjud bo'lsa)
        _clear_dashboard_cache()
        logger.info("MV lar sinxron yangilandi")
    except Exception as e:
        logger.warning("MV refresh xatolik (normal holatda Celery ishlatilsin): %s", e)
