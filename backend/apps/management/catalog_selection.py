from django.core.files.base import ContentFile
from pathlib import Path
from apps.landing.models import Product
from apps.landing.catalog_data import product_data


def catalog_context():
    return {'products_data':[product_data(product,private=True) for product in Product.objects.select_related('mtm_category').all()]}


def product_initial(product):
    return {'reference_product':product.pk,'product_category':product.mtm_category_id,'title':product.name,
        'description':product.description,'quantity':1,'unit_price':product.price,
        'unit_filament_g':product.unit_filament_g,'unit_print_hours':product.unit_print_hours}


def save_product_images(entry):
    lines=list(entry.items.select_related('product','variant__product'))
    if not entry.reference_product_id and len(lines)==1 and lines[0].product_id:
        entry.reference_product=lines[0].product;entry.product_category=lines[0].product.mtm_category
        entry.save(update_fields=['reference_product','product_category','updated_at'])
    def copy(source,target):
        if source and not target:
            with source.open('rb') as file:target.save('referencia'+Path(source.name).suffix,ContentFile(file.read()),save=True)
    if entry.reference_product_id:copy(entry.reference_product.image,entry.image)
    for line in lines:
        source=line.variant.image if line.variant_id and line.variant.image else line.product.image if line.product_id else None
        copy(source,line.image)
