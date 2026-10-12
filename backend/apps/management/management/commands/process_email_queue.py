from django.core.management.base import BaseCommand
from apps.landing.notifications import dispatch_contact_emails
from apps.management.workflow import dispatch_emails
class Command(BaseCommand):
    help='Procesa las dos colas de correo sin reenviar mensajes ya aceptados. Ejecutar mediante cron.'
    def handle(self,*args,**options):
        self.stdout.write(f'Solicitudes aceptadas: {dispatch_contact_emails()}. Avisos aceptados: {dispatch_emails()}.')
