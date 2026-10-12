from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
class Command(BaseCommand):
    help='Comprueba configuración del flujo sin enviar correos ni revelar credenciales.'
    def handle(self,*args,**options):
        try:
            validate_email(settings.CONTACT_NOTIFICATION_EMAIL)
            if settings.CONTACT_NOTIFICATION_EMAIL.endswith('@localhost'):raise ValidationError('Destinatario local')
        except ValidationError:raise CommandError('CONTACT_NOTIFICATION_EMAIL no contiene un destinatario válido.')
        self.stdout.write(f'Proveedor: {settings.EMAIL_PROVIDER}; backend: {settings.EMAIL_BACKEND}')
        if settings.EMAIL_BACKEND.endswith('GmailAPIEmailBackend') and not all(getattr(settings,key,'') for key in ('GMAIL_CLIENT_ID','GMAIL_CLIENT_SECRET','GMAIL_REFRESH_TOKEN')):
            raise CommandError('Faltan credenciales Gmail API en las variables del servicio.')
        self.stdout.write('Destinatario interno válido. Configuración comprobada; no se envió ningún correo.')
