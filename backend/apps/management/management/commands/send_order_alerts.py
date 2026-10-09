from django.core.management.base import BaseCommand
from apps.management.workflow import queue_daily_digest, dispatch_emails

class Command(BaseCommand):
    help = 'Envía un resumen diario de pedidos pendientes y fechas próximas. No duplica el resumen del día.'
    def handle(self, *args, **options):
        message = queue_daily_digest()
        sent = dispatch_emails(message.pk) if message else 0
        self.stdout.write(f'Resumen aceptado: {sent}. Sin pedidos activos: {message is None}.')
