"""Persisted messages: mail failures never discard the customer's request."""
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from .models import ContactEmail

logger = logging.getLogger(__name__)

def queue_contact_emails(contact, entry):
    admin = settings.CONTACT_NOTIFICATION_EMAIL
    url = settings.PUBLIC_SITE_URL.rstrip('/') + reverse('management:quote_detail', args=[entry.pk])
    for audience, recipient, subject in [
        ('customer', contact.email, f'VillaTech · Recibimos tu solicitud #{contact.pk}'),
        ('admin', admin, f'VillaTech · Nueva solicitud web #{contact.pk}'),
    ]:
        context = {'contact': contact, 'entry': entry, 'admin': audience == 'admin', 'management_url': url}
        ContactEmail.objects.create(contact=contact, audience=audience, recipient=recipient,
            subject=subject, text=render_to_string('landing/emails/contact.txt',context),
            html=render_to_string('landing/emails/contact.html',context),
            reply_to=contact.email if audience == 'admin' else admin)

def dispatch_contact_emails(contact_id=None):
    pending = ContactEmail.objects.exclude(status='sent')
    if contact_id is not None:
        pending = pending.filter(contact_id=contact_id)
    sent = 0
    for pk in list(pending.order_by('pk').values_list('pk', flat=True)):
        # Lock prevents the web request and a manual retry from sending concurrently.
        with transaction.atomic():
            message = ContactEmail.objects.select_for_update().get(pk=pk)
            if message.status == 'sent':
                continue
            if message.audience == 'admin' and not message.recipient:
                message.recipient = settings.CONTACT_NOTIFICATION_EMAIL
            message.attempts += 1
            try:
                validate_email(message.recipient)
                connection = get_connection()
                if settings.EMAIL_HOST == 'smtp.gmail.com' and hasattr(connection, 'password'):
                    connection.password = ''.join((connection.password or '').split())
                mail = EmailMultiAlternatives(message.subject,message.text,settings.DEFAULT_FROM_EMAIL,
                    [message.recipient], connection=connection, reply_to=[message.reply_to] if message.reply_to else [],
                    headers={'Idempotency-Key': f'villatech-contact-{message.contact_id}-{message.audience}'})
                mail.attach_alternative(message.html,'text/html')
                if mail.send(fail_silently=False) != 1:
                    raise RuntimeError('El proveedor no aceptó el correo')
            except Exception as error:
                message.status = 'failed'
                # No credentials, provider bodies, or customer data in logs.
                message.last_error = type(error).__name__
                logger.warning('Contact email %s failed (%s)',message.pk,message.last_error)
            else:
                message.status = 'sent'; message.sent_at = timezone.now(); message.last_error = ''; sent += 1
            message.save(update_fields=['recipient','status','attempts','last_error','sent_at'])
    return sent

def safely_dispatch(contact_id):
    try:
        dispatch_contact_emails(contact_id)
    except Exception:
        logger.exception('Could not dispatch persisted messages for contact %s',contact_id)
