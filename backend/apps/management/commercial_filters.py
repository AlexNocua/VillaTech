from django.db.models import F

PAYMENT_CHOICES=[('pending','Con saldo pendiente'),('unpaid','Sin pago'),('partial','Con abono parcial'),('paid','Pagados / liquidados')]


def filter_payment(entries,value):
    if value not in dict(PAYMENT_CHOICES):return entries
    entries=entries.filter(kind__in=['order','sale']).exclude(status='cancelled')
    if value=='paid':return entries.filter(amount__gt=0,paid_amount__gte=F('amount'))
    entries=entries.filter(amount__gt=F('paid_amount'))
    if value=='unpaid':entries=entries.filter(paid_amount=0)
    elif value=='partial':entries=entries.filter(paid_amount__gt=0)
    return entries
