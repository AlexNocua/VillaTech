from django.urls import reverse
from .models import Product


def public_products():
    return Product.objects.filter(is_active=True,is_public=True,mtm_category__is_active=True).select_related('mtm_category')


def quote_text(product):
    return f'Me interesa cotizar: {product.name}\nCategoría: {product.mtm_category.category_name}\n\n{product.description}\n\nCantidad y personalización: '


def product_data(product,private=False):
    return {'id':product.pk,'name':product.name,'description':product.description,
        'category_id':product.mtm_category_id,'category':product.mtm_category.category_name,
        'price':str(product.price),'unit_filament_g':str(product.unit_filament_g),'unit_print_hours':str(product.unit_print_hours),
        'image':reverse('management:product_image',args=[product.pk]) if private and product.image else product.display_image_url,
        'detail_url':reverse('landing:product_detail',args=[product.pk]),'quote_text':quote_text(product)}
