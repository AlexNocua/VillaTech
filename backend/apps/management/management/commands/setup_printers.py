from django.core.management.base import BaseCommand
from apps.management.models import PrinterProfile
class Command(BaseCommand):
    def handle(self,*args,**kwargs):
        for name,watts in [('Creality K1C',350),('Flashforge Creator 5 Pro',1200)]:
            PrinterProfile.objects.get_or_create(name=name,defaults={'rated_watts':watts})
        self.stdout.write(self.style.SUCCESS('Perfiles listos. Configura costos y consumo medio.'))
