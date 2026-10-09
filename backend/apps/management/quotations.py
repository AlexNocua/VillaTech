"""Single quotation-to-order lifecycle. Approval links only change data on POST."""
import uuid
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from .models import Entry, OperationalEmail, EntryActivity
from .workflow import approve_order, estimate_delivery, schedule_dispatch

SALT='villatech.quotation.approval.v1'

def approval_token(entry):
    return signing.dumps({'id':entry.pk,'nonce':str(entry.approval_nonce)},salt=SALT,compress=True)

def approval_url(entry):
    return settings.PUBLIC_SITE_URL.rstrip('/')+reverse('management:customer_quote',args=[approval_token(entry)])

def entry_from_token(token,lock=False):
    try:
        data=signing.loads(token,salt=SALT,max_age=48*60*60)
        qs=Entry.objects.select_for_update() if lock else Entry.objects
        return qs.get(pk=data['id'],approval_nonce=data['nonce'])
    except (signing.BadSignature,KeyError,ValueError,TypeError,Entry.DoesNotExist):
        raise ValidationError('El enlace ya no es válido. Solicita una nueva cotización a VillaTech.') from None

def recalculate(entry):
    lines=list(entry.items.all())
    entry.amount=sum((i.total for i in lines),Decimal(0)) if lines else entry.quantity*entry.unit_price
    # Legacy jobs retain their saved total until per-unit data is entered.
    entry.filament_g=sum((i.filament_total for i in lines),Decimal(0)) if lines and any(i.unit_filament_g for i in lines) else entry.quantity*entry.unit_filament_g
    entry.print_hours=sum((i.hours_total for i in lines),Decimal(0)) if lines and any(i.unit_print_hours for i in lines) else entry.quantity*entry.unit_print_hours
    if entry.amount < entry.paid_amount:
        raise ValidationError('El total no puede ser menor que los abonos registrados.')
    if entry.amount>Decimal('999999999999.99') or entry.filament_g>Decimal('99999999.99') or entry.print_hours>Decimal('99999999.99'):
        raise ValidationError('La cantidad produce un total fuera del límite permitido.')
    entry.save(update_fields=['amount','filament_g','print_hours','updated_at'])

def expire_quotes():
    count=0
    for pk in list(Entry.objects.filter(kind='quote',status='sent',quote_expires_at__lte=timezone.now()).values_list('pk',flat=True)):
        with transaction.atomic():
            entry=Entry.objects.select_for_update().get(pk=pk)
            if entry.kind!='quote' or entry.status!='sent' or entry.quote_expires_at>timezone.now():continue
            entry.status='expired';entry.save(update_fields=['status','updated_at'])
            EntryActivity.objects.create(entry=entry,label='Cotización vencida',note='Sin aprobación durante las 48 horas de vigencia.')
            OperationalEmail.objects.filter(entry=entry,event_key__startswith='quote:',status__in=['pending','failed']).update(status='skipped',last_error='Cotización vencida; prepara una nueva versión.')
            count+=1
    return count

def send_quotation(entry,actor):
    if entry.kind!='quote' or entry.status not in ('quoted','sent'):
        raise ValidationError('Prepara la cotización antes de enviarla. Las vencidas requieren una nueva versión.')
    if not entry.customer_email:
        raise ValidationError('Agrega el correo del cliente antes de enviar la cotización.')
    if entry.amount<=0:
        raise ValidationError('Registra el precio de la cotización antes de enviarla.')
    if entry.status=='sent':
        if entry.quote_expires_at and entry.quote_expires_at<=timezone.now():
            raise ValidationError('La cotización venció. Prepara una nueva versión.')
        return OperationalEmail.objects.get(event_key=f'quote:{entry.pk}:{entry.approval_nonce}')
    entry.quote_sent_at=timezone.now();entry.quote_expires_at=entry.quote_sent_at+timedelta(hours=48)
    entry.status='sent';entry.quotation_pdf=''
    entry.save(update_fields=['quote_sent_at','quote_expires_at','status','quotation_pdf','updated_at'])
    context={'entry':entry,'heading':'Tu cotización está lista','approval_url':approval_url(entry)}
    message=OperationalEmail.objects.create(entry=entry,event_key=f'quote:{entry.pk}:{entry.approval_nonce}',
        recipient=entry.customer_email,subject=f'VillaTech · Cotización VT-{entry.pk:06d}',
        text=render_to_string('management/emails/quotation.txt',context),
        html=render_to_string('management/emails/quotation.html',context))
    from .quotation import build_quote
    message.attachment.save(f'VillaTech-cotizacion-{entry.pk}.pdf',ContentFile(build_quote(entry)),save=True)
    EntryActivity.objects.create(entry=entry,label='Cotización enviada a la cola',actor=actor,note='Vigencia de 48 horas desde este envío. Revisa el estado del correo.')
    return message

def confirm_quotation(entry,channel='internal',note='',actor=None,date=None):
    if entry.kind=='order' and entry.approved_at:return False
    if entry.kind!='quote' or entry.status not in ('quoted','sent'):
        raise ValidationError('Esta cotización no admite aprobación. Solicita una nueva versión si venció.')
    if entry.quote_expires_at and entry.quote_expires_at<=timezone.now():
        raise ValidationError('La cotización venció y ya no puede aprobarse.')
    if channel=='email' and entry.status!='sent':
        raise ValidationError('La cotización no está disponible para confirmación por correo.')
    if entry.amount<=0:raise ValidationError('Define el precio antes de confirmar.')
    entry.kind='order';entry.status='pending';entry.approval_channel=channel;entry.approval_note=note[:255]
    proposed=date or entry.estimated_delivery_date
    entry.estimated_delivery_date=proposed if proposed and proposed>=timezone.localdate() else estimate_delivery(entry)
    entry.save()
    schedule_dispatch(approve_order(entry))
    EntryActivity.objects.create(entry=entry,label='Pedido confirmado',note=f'{dict(Entry._meta.get_field("approval_channel").choices).get(channel,channel)} · {note}'[:255],actor=actor)
    return True

def renew_quotation(entry,actor):
    if entry.kind!='quote' or entry.status not in ('sent','expired','quoted'):
        raise ValidationError('Solo se pueden renovar cotizaciones sin aprobar.')
    entry.approval_nonce=uuid.uuid4();entry.status='quoted';entry.quote_sent_at=None;entry.quote_expires_at=None
    entry.save(update_fields=['approval_nonce','status','quote_sent_at','quote_expires_at','updated_at'])
    OperationalEmail.objects.filter(entry=entry,event_key__startswith='quote:',status__in=['pending','failed']).update(status='skipped',last_error='Versión sustituida.')
    EntryActivity.objects.create(entry=entry,label='Nueva versión de cotización',actor=actor,note='Los enlaces anteriores quedan invalidados.')
