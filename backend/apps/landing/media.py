from django.http import FileResponse, Http404
from .models import Product, ProductVariant

def catalog_image(request, name):
    filename = 'catalog/' + name
    product = Product.objects.filter(image=filename, is_active=True, is_public=True, mtm_category__is_active=True).first()
    variant = None if product else ProductVariant.objects.filter(image=filename, is_active=True, product__is_active=True, product__is_public=True, product__mtm_category__is_active=True).first()
    item = product or variant
    if not item:
        raise Http404
    try:
        stream = item.image.open('rb')
    except FileNotFoundError:
        raise Http404('Imagen no disponible.')
    response = FileResponse(stream)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'public, max-age=3600'
    return response
