from django.core.management.base import BaseCommand,CommandError
from apps.management.models import Entry
from apps.management.workflow import queue_owner_order,dispatch_emails
class Command(BaseCommand):
    help='Prepara el aviso interno faltante para un pedido específico; no duplica avisos aceptados.'
    def add_arguments(self,parser):parser.add_argument('order_id',type=int)
    def handle(self,*args,**options):
        entry=Entry.objects.filter(pk=options['order_id'],kind__in=['order','sale']).first()
        if not entry:raise CommandError('Pedido o venta no encontrado.')
        message=queue_owner_order(entry)
        self.stdout.write(f'Aviso interno aceptado: {dispatch_emails(message.pk)}.')
