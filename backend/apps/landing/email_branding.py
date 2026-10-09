"""One branded composer for contact receipts, order updates and owner alerts."""
import logging
from email.mime.image import MIMEImage
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)

def branded_mail(subject, text, recipient, html, *, connection=None, reply_to=None, key=''):
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [recipient],
        connection=connection, reply_to=[reply_to] if reply_to else [],
        headers={'Idempotency-Key': key} if key else {})
    message.attach_alternative(html, 'text/html')
    # Original logo is embedded: customers need no session or public media URL.
    path = finders.find('landing/images/logo-light-transparent.png')
    if path:
        with open(path, 'rb') as logo_file:
            logo = MIMEImage(logo_file.read(), _subtype='png')
        logo.add_header('Content-ID', '<villatech-logo>')
        logo.add_header('Content-Disposition', 'inline', filename='villatech-logo.png')
        message.attach(logo)
        message.mixed_subtype = 'related'
    else:
        logger.warning('VillaTech email logo not found in static assets')
    return message
