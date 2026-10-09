from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
import logging
from django.conf import settings
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Sum
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from apps.landing.email_branding import branded_mail
from apps.landing.mail_diagnostics import mail_error_summary, safe_error_code
from .models import Entry, OperationalEmail

logger = logging.getLogger(__name__)
ACTIVE_STATUSES = ('pending', 'printing', 'ready')

def active_orders():
    return Entry.objects.filter(kind='order', status__in=ACTIVE_STATUSES)

def estimate_delivery(entry, today=None):
    """One production queue, eight hours/day, plus one day for finishing.

    No printing time: three working days. Weekends excluded; dates remain editable.
    Existing promised dates are respected when placing a new order at queue end.
    """
    today = today or timezone.localdate()
    others = active_orders().exclude(pk=entry.pk)
    hours = others.aggregate(total=Sum('print_hours'))['total'] or Decimal(0)
    total = hours + (entry.print_hours or Decimal(0))
    days = max(1, int((total / Decimal(8)).to_integral_value(rounding=ROUND_CEILING))) + 1
    if not entry.print_hours:
        days = max(3, days)
    proposed = today
    for _ in range(days):
        proposed += timedelta(days=1)
        while proposed.weekday() >= 5:
            proposed += timedelta(days=1)
    last = others.filter(estimated_delivery_date__isnull=False).order_by('-estimated_delivery_date').first()
    if last and last.estimated_delivery_date >= proposed:
        proposed = last.estimated_delivery_date + timedelta(days=1)
        while proposed.weekday() >= 5:
            proposed += timedelta(days=1)
    return proposed

def queue_order_email(entry, event):
    if not entry.customer_email:
        return None
    # A saved revision generates a new snapshot; repeated submissions do not resend it.
    version = entry.updated_at.isoformat() if event != 'approved' else 'first'
    key = f'order:{entry.pk}:{event}:{version}'
    titles = {'approved':'Pedido confirmado', 'updated':'Actualización de tu pedido',
              'delivered':'Pedido entregado', 'cancelled':'Pedido cancelado'}
    context = {'entry':entry, 'heading':titles[event], 'event':event}
    return OperationalEmail.objects.get_or_create(event_key=key, defaults={
        'entry':entry, 'recipient':entry.customer_email,
        'subject':f'VillaTech · {titles[event]} #{entry.pk}',
        'text':render_to_string('management/emails/order.txt',context),
        'html':render_to_string('management/emails/order.html',context)})[0]

def approve_order(entry):
    if entry.kind != 'order' or entry.status not in ACTIVE_STATUSES:
        return None
    first = entry.approved_at is None
    if first:
        entry.approved_at = timezone.now()
    if not entry.estimated_delivery_date:
        entry.estimated_delivery_date = estimate_delivery(entry)
    entry.save(update_fields=['approved_at','estimated_delivery_date','updated_at'])
    return queue_order_email(entry,'approved') if first else None

def schedule_dispatch(message):
    if message:
        transaction.on_commit(lambda pk=message.pk: safely_dispatch(pk))

def dispatch_emails(pk=None):
    pending = OperationalEmail.objects.exclude(status='sent')
    if pk is not None:
        pending = pending.filter(pk=pk)
    sent = 0
    for message_pk in list(pending.order_by('pk').values_list('pk',flat=True)):
        with transaction.atomic():
            message = OperationalEmail.objects.select_for_update().get(pk=message_pk)
            if message.status == 'sent':
                continue
            if not message.recipient and message.event_key.startswith('digest:'):
                message.recipient = settings.CONTACT_NOTIFICATION_EMAIL
            message.attempts += 1
            try:
                validate_email(message.recipient)
                mail = branded_mail(message.subject,message.text,message.recipient,message.html,
                    reply_to=settings.CONTACT_NOTIFICATION_EMAIL, key='villatech-'+message.event_key)
                if mail.send(fail_silently=False) != 1:
                    raise RuntimeError('El proveedor no aceptó el correo')
            except Exception as error:
                message.status = 'failed'
                message.last_error = mail_error_summary(error)[:160]
                logger.warning('Operational email %s failed (%s): %s',message.pk,safe_error_code(error),message.last_error)
            else:
                message.status = 'sent'
                message.sent_at = timezone.now()
                message.last_error = ''
                sent += 1
            message.save(update_fields=['recipient','attempts','status','last_error','sent_at'])
    return sent

def safely_dispatch(pk):
    try:
        dispatch_emails(pk)
    except Exception:
        logger.exception('Could not dispatch operational email %s',pk)

def queue_daily_digest(today=None):
    today = today or timezone.localdate()
    orders = active_orders().order_by('estimated_delivery_date','created_at')
    # No idle daily emails; the dashboard always displays zero counts.
    if not orders.exists():
        return None
    urgent = orders.filter(estimated_delivery_date__lte=today+timedelta(days=3))
    context = {'heading':'Agenda de pedidos', 'today':today, 'pending':orders.count(),
        'overdue':orders.filter(estimated_delivery_date__lt=today).count(),
        'due_today':orders.filter(estimated_delivery_date=today).count(),
        'upcoming':orders.filter(estimated_delivery_date__gt=today,estimated_delivery_date__lte=today+timedelta(days=3)).count(),
        'undated':orders.filter(estimated_delivery_date__isnull=True).count(),
        'urgent':list(urgent[:100]),'truncated':urgent.count()>100,
        'management_url':settings.PUBLIC_SITE_URL.rstrip('/')+reverse('management:orders')}
    return OperationalEmail.objects.get_or_create(event_key=f'digest:{today.isoformat()}',defaults={
        'recipient':settings.CONTACT_NOTIFICATION_EMAIL,
        'subject':f'VillaTech · {context["pending"]} pedidos pendientes · {today:%d/%m/%Y}',
        'text':render_to_string('management/emails/digest.txt',context),
        'html':render_to_string('management/emails/digest.html',context)})[0]
