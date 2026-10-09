from django.core.management.base import BaseCommand
from apps.management.workflow import dispatch_emails
from apps.management.models import OperationalEmail

class Command(BaseCommand):
    help = 'Reintenta avisos de pedidos y resúmenes pendientes o fallidos.'
    def handle(self,*args,**options):
        sent = dispatch_emails()
        self.stdout.write(f'Aceptados: {sent}. Pendientes/fallidos: {OperationalEmail.objects.filter(status__in=["pending","failed"]).count()}.')
