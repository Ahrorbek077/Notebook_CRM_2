# notebook/company/services.py
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from .models import Company, Branch, BranchPayment
from notebook.activity.models import ActivityLog


def _sync_company_balances(company_id: int):
    """
    Kompaniya total_debt va advance_balance ni filiallar
    yig'indisidan qayta hisoblaydi.
    """
    agg = Branch.objects.filter(
        company_id=company_id, is_active=True
    ).aggregate(
        debt=Sum('total_debt'),
        adv=Sum('advance_balance'),
    )
    Company.objects.filter(pk=company_id).update(
        total_debt      = agg['debt'] or Decimal('0'),
        advance_balance = agg['adv']  or Decimal('0'),
    )


class CompanyService:

    @staticmethod
    def create_company(name, business=None, phone="", address="", note="", user=None) -> Company:
        with transaction.atomic():
            c = Company.objects.create(
                name=name, business=business, phone=phone, address=address, note=note, created_by=user
            )
            ActivityLog.objects.create(
                user=user, business=c.business, action_type='company_create',
                description=f"Kompaniya qo'shildi: {name}",
                extra_data={'company_id': c.id, 'name': name}
            )
            return c

    @staticmethod
    def update_company(company: Company, data: dict, user=None) -> Company:
        for k, v in data.items():
            setattr(company, k, v)
        company.save()
        ActivityLog.objects.create(
            user=user, business=company.business, action_type='company_update',
            description=f"Kompaniya yangilandi: {company.name}",
            extra_data={'company_id': company.id, **data}
        )
        return company

    @staticmethod
    def delete_company(company: Company, user=None):
        company.is_active = False
        company.save(update_fields=['is_active'])
        ActivityLog.objects.create(
            user=user, business=company.business, action_type='company_delete',
            description=f"Kompaniya o'chirildi: {company.name}",
            extra_data={'company_id': company.id}
        )

    @staticmethod
    def create_branch(company: Company, name, phone="", address="", note="", user=None) -> Branch:
        with transaction.atomic():
            b = Branch.objects.create(
                company=company, name=name, phone=phone,
                address=address, note=note, created_by=user
            )
            ActivityLog.objects.create(
                user=user, business=company.business, action_type='branch_create',
                description=f"Filial qo'shildi: {company.name} — {name}",
                extra_data={'branch_id': b.id, 'company_id': company.id, 'name': name}
            )
            return b

    @staticmethod
    def update_branch(branch: Branch, data: dict, user=None) -> Branch:
        for k, v in data.items():
            setattr(branch, k, v)
        branch.save()
        ActivityLog.objects.create(
            user=user, business=branch.company.business, action_type='branch_update',
            description=f"Filial yangilandi: {branch}",
            extra_data={'branch_id': branch.id, **data}
        )
        return branch

    @staticmethod
    def delete_branch(branch: Branch, user=None):
        branch.is_active = False
        branch.save(update_fields=['is_active'])
        ActivityLog.objects.create(
            user=user, business=branch.company.business, action_type='branch_delete',
            description=f"Filial o'chirildi: {branch}",
            extra_data={'branch_id': branch.id}
        )

    # ─────────────────────────────────────────────────────────────
    # TO'LOV: biz filialga pul to'laymiz
    #   Avvalo avans (advance_balance) dan ayiramiz,
    #   qolgan qismni qarzdan (total_debt) ayiramiz,
    #   to'lov qarzdan ko'p bo'lsa — ortiqcha avansga tushadi.
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def pay_to_branch(branch: Branch, amount: Decimal,
                      payment_type='cash', discount_percent=Decimal('0'),
                      due_date=None, note="", user=None) -> BranchPayment:
        if amount <= 0:
            raise ValueError("To'lov summasi musbat bo'lishi kerak")

        with transaction.atomic():
            branch = Branch.objects.select_for_update().get(pk=branch.pk)

            bp = BranchPayment.objects.create(
                branch=branch, amount=amount, payment_type=payment_type,
                discount_percent=discount_percent, due_date=due_date,
                note=note, user=user
            )

            if payment_type == 'discount':
                # ──────────────────────────────────────────────────────────
                # CHEGIRMA: haqiqiy pul to'lanmaydi.
                # Qarz shunchaki kamayadi (avansga ta'sir yo'q, naqd/bank yo'q).
                # 100 000 qarz bor, 25 000 chegirma → qarz 75 000 bo'ladi.
                # ──────────────────────────────────────────────────────────
                if branch.total_debt >= amount:
                    branch.total_debt -= amount
                else:
                    # Qarzdan ko'p chegirma berildi → ortiqcha avansga
                    overpaid = amount - branch.total_debt
                    branch.total_debt      = Decimal('0')
                    branch.advance_balance += overpaid
            else:
                # ──────────────────────────────────────────────────────────
                # NAQD / BANK TO'LOV: avvalo avansni ishlatamiz,
                # qolganini qarzdan ayiramiz.
                # ──────────────────────────────────────────────────────────
                remaining = amount
                if branch.advance_balance > 0:
                    use_adv = min(branch.advance_balance, remaining)
                    branch.advance_balance -= use_adv
                    remaining -= use_adv

                if remaining > 0:
                    if branch.total_debt >= remaining:
                        branch.total_debt -= remaining
                    else:
                        # Qarz tugab, ortiqcha to'lov → avans
                        overpaid = remaining - branch.total_debt
                        branch.total_debt      = Decimal('0')
                        branch.advance_balance += overpaid

            branch.save(update_fields=['total_debt', 'advance_balance'])
            _sync_company_balances(branch.company_id)

            type_label = {'cash': 'naqd', 'transfer': "o'tkazma", 'discount': 'chegirma'}.get(payment_type, payment_type)
            ActivityLog.objects.create(
                user=user, business=branch.company.business, action_type='branch_payment',
                description=f"{branch} — {amount:,.0f} so'm {type_label} ({payment_type})",
                extra_data={
                    'branch_payment_id': bp.id, 'branch_id': branch.id, 'branch_name': str(branch),
                    'amount': str(amount), 'payment_type': payment_type,
                    'new_debt': str(branch.total_debt),
                    'new_advance': str(branch.advance_balance),
                }
            )
            return bp

    # ─────────────────────────────────────────────────────────────
    # XARID: biz filialdan mahsulot olamiz → qarz oshadi
    #   Avvalo avansdan ayiramiz (agar bor bo'lsa),
    #   keyin qolganini qarzga qo'shamiz.
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def record_purchase(branch: Branch, amount: Decimal, user=None):
        """
        Sotib olinganida chaqiriladi.
        amount = quantity × cost_price
        """
        with transaction.atomic():
            branch = Branch.objects.select_for_update().get(pk=branch.pk)

            # Avvalo avansdan foydalanamiz
            if branch.advance_balance >= amount:
                branch.advance_balance -= amount
            else:
                remaining = amount - branch.advance_balance
                branch.advance_balance = Decimal('0')
                branch.total_debt     += remaining

            branch.save(update_fields=['total_debt', 'advance_balance'])
            _sync_company_balances(branch.company_id)

            ActivityLog.objects.create(
                user=user, business=branch.company.business, action_type='stock_add',
                description=f"{branch} — {amount:,.0f} so'm xarid (qarz yoki avansdan)",
                extra_data={
                    'branch_id': branch.id, 'branch_name': str(branch),
                    'amount': str(amount),
                    'new_debt': str(branch.total_debt),
                    'new_advance': str(branch.advance_balance),
                }
            )

    # ─────────────────────────────────────────────────────────────
    # QAYTARISH: biz filialga mahsulot qaytaramiz → qarz kamayadi
    #   Avvalo qarzdan ayiramiz,
    #   qarz 0 ga tushsa — ortiqcha summa avansga tushadi.
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def record_return(branch: Branch, amount: Decimal, user=None):
        """
        Xarid qaytarilganda chaqiriladi.
        amount = qaytarilgan_miqdor × cost_price
        """
        with transaction.atomic():
            branch = Branch.objects.select_for_update().get(pk=branch.pk)

            if branch.total_debt >= amount:
                branch.total_debt -= amount
            else:
                # Qarzdan ko'p qaytarildi → ortiqcha avansga
                overpaid = amount - branch.total_debt
                branch.total_debt      = Decimal('0')
                branch.advance_balance += overpaid

            branch.save(update_fields=['total_debt', 'advance_balance'])
            _sync_company_balances(branch.company_id)

            ActivityLog.objects.create(
                user=user, business=branch.company.business, action_type='stock_return',
                description=f"{branch} — {amount:,.0f} so'm qaytarildi",
                extra_data={
                    'branch_id': branch.id, 'branch_name': str(branch),
                    'amount': str(amount),
                    'new_debt': str(branch.total_debt),
                    'new_advance': str(branch.advance_balance),
                }
            )