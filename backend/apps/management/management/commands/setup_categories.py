from django.core.management.base import BaseCommand
from apps.landing.models import CategoryProduct
class Command(BaseCommand):
    help='Crea las categorías iniciales sin modificar productos existentes.'
    def handle(self,*args,**kwargs):
        for name in ['Llaveros','Técnicos','Figuras']:
            CategoryProduct.objects.get_or_create(category_name=name)
        self.stdout.write(self.style.SUCCESS('Categorías listas.'))
