# notebook/expenses/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.timezone import now
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
import datetime, json

from .models import PersonalExpense

PAGE_SIZE = 15


# ── Sahifa ─────────────────────────────────────────────────────────────────────

@login_required
def expenses_page(request):
    existing_cats = (
        PersonalExpense.objects
        .filter(user=request.user)
        .exclude(category='')
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    return render(request, 'expenses/expenses.html', {
        'today':         now().date(),
        'existing_cats': list(existing_cats),
    })


# ── API: Chiqim qo'shish ───────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def expense_create(request):
    try:
        data        = json.loads(request.body)
        description = data.get('description', '').strip()
        amount      = data.get('amount')
        date_str    = data.get('date') or str(now().date())
        category    = data.get('category', '').strip()

        if not description:
            return JsonResponse({'status': 'error', 'message': 'Tavsif kiritilmadi'}, status=400)
        if not amount or float(amount) <= 0:
            return JsonResponse({'status': 'error', 'message': "Miqdor noto'g'ri"}, status=400)

        expense = PersonalExpense.objects.create(
            user=request.user,
            description=description,
            amount=amount,
            date=date_str,
            category=category,
        )
        return JsonResponse({'status': 'created', 'expense': _to_dict(expense)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ── API: O'chirish ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['DELETE'])
def expense_delete(request, pk):
    try:
        PersonalExpense.objects.get(pk=pk, user=request.user).delete()
        return JsonResponse({'status': 'deleted'})
    except PersonalExpense.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Topilmadi'}, status=404)


# ── API: Ro'yxat + search + pagination ────────────────────────────────────────

@login_required
def expense_list(request):
    """
    period : today | week | month | year | all
    q      : search (description yoki category bo'yicha)
    page   : 1-based (default 1)
    """
    period = request.GET.get('period', 'today')
    q      = request.GET.get('q', '').strip()
    page   = max(1, int(request.GET.get('page', 1)))
    today  = now().date()

    qs = PersonalExpense.objects.filter(user=request.user)

    # Period filter
    if period == 'today':
        qs = qs.filter(date=today)
    elif period == 'week':
        qs = qs.filter(date__gte=today - datetime.timedelta(days=today.weekday()))
    elif period == 'month':
        qs = qs.filter(date__year=today.year, date__month=today.month)
    elif period == 'year':
        qs = qs.filter(date__year=today.year)

    # Search filter
    if q:
        qs = qs.filter(
            Q(description__icontains=q) | Q(category__icontains=q)
        )

    total      = qs.aggregate(t=Sum('amount'))['t'] or 0
    count      = qs.count()
    total_pages = max(1, (count + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = min(page, total_pages)
    offset      = (page - 1) * PAGE_SIZE

    expenses = [_to_dict(e) for e in qs[offset: offset + PAGE_SIZE]]

    return JsonResponse({
        'status':      'ok',
        'total':       float(total),
        'count':       count,
        'page':        page,
        'total_pages': total_pages,
        'has_next':    page < total_pages,
        'has_prev':    page > 1,
        'expenses':    expenses,
    })


# ── API: Statistika ────────────────────────────────────────────────────────────

@login_required
def expense_stats(request):
    group = request.GET.get('group', 'month')
    today = now().date()
    user  = request.user

    if group == 'week':
        date_from = today - datetime.timedelta(days=6)
        rows   = (
            PersonalExpense.objects
            .filter(user=user, date__gte=date_from, date__lte=today)
            .values('date')
            .annotate(total=Sum('amount'))
            .order_by('date')
        )
        totals = {r['date']: float(r['total']) for r in rows}
        labels, values = [], []
        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            labels.append(d.strftime('%d-%b'))
            values.append(totals.get(d, 0.0))

    elif group == 'month':
        date_from = today.replace(day=1)
        rows   = (
            PersonalExpense.objects
            .filter(user=user, date__gte=date_from, date__lte=today)
            .values('date')
            .annotate(total=Sum('amount'))
            .order_by('date')
        )
        totals = {r['date']: float(r['total']) for r in rows}
        labels, values = [], []
        d = date_from
        while d <= today:
            labels.append(str(d.day))
            values.append(totals.get(d, 0.0))
            d += datetime.timedelta(days=1)

    else:  # year
        rows   = (
            PersonalExpense.objects
            .filter(user=user, date__year=today.year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )
        totals      = {r['month'].month: float(r['total']) for r in rows}
        month_names = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']
        labels      = month_names
        values      = [totals.get(m, 0.0) for m in range(1, 13)]

    cat_rows = (
        PersonalExpense.objects
        .filter(user=user, date__year=today.year, date__month=today.month)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    return JsonResponse({
        'status': 'ok',
        'group':  group,
        'chart':  {'labels': labels, 'values': values},
        'by_category': {
            'labels': [c['category'] or 'Boshqa' for c in cat_rows],
            'values': [float(c['total']) for c in cat_rows],
        },
    })


# ── Helper ─────────────────────────────────────────────────────────────────────

def _to_dict(e):
    return {
        'id':          e.id,
        'description': e.description,
        'amount':      float(e.amount),
        'date':        str(e.date),
        'category':    e.category or '',
    }