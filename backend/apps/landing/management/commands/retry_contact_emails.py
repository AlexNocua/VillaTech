from django.core.management.base import BaseCommand
from apps.landing.notifications import dispatch_contact_emails
from apps.landing.models import ContactEmail

class Command(BaseCommand):
    help = 'Reintenta correos pendientes/fallidos; omite los aceptados por el proveedor.'
    def handle(self, *args, **options):
        sent = dispatch_contact_emails()
        remaining = ContactEmail.objects.exclude(status='sent').count()
        self.stdout.write(f'Aceptados: {sent}. Pendientes/fallidos: {remaining}.')
