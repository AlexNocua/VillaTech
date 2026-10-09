from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import get_connection
from apps.landing.mail_diagnostics import mail_error_summary, safe_error_code

class Command(BaseCommand):
    help='Comprueba el acceso al servidor SMTP sin enviar mensajes ni mostrar credenciales.'
    def handle(self,*args,**options):
        if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
            raise CommandError('El transporte activo no es SMTP. Revisa EMAIL_PROVIDER y EMAIL_BACKEND.')
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError('Falta EMAIL_HOST_USER o EMAIL_HOST_PASSWORD. Configúralas en el servidor.')
        connection=get_connection(fail_silently=False)
        if settings.EMAIL_HOST == 'smtp.gmail.com':
            connection.password=''.join((connection.password or '').split())
        try:
            connection.open()
        except Exception as error:
            raise CommandError(mail_error_summary(error)+' ['+safe_error_code(error)+']') from None
        finally:
            connection.close()
        self.stdout.write(self.style.SUCCESS('Conexión y autenticación SMTP correctas. No se envió ningún correo.'))
