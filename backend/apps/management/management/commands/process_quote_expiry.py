from django.core.management.base import BaseCommand
from apps.management.quotations import expire_quotes
class Command(BaseCommand):
    help='Cancela como vencidas las cotizaciones enviadas sin aprobar durante 48 horas.'
    def handle(self,*args,**options):self.stdout.write(f'Cotizaciones vencidas: {expire_quotes()}.')
