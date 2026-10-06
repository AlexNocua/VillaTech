from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from .models import ProductVariant

def catalog_image(request,name):
    variant=ProductVariant.objects.filter(image='catalog/'+name,is_active=True,product__is_active=True,product__is_public=True).first()
    if not variant: raise Http404
    response=FileResponse(variant.image.open('rb'))
    response['X-Content-Type-Options']='nosniff'
    response['Cache-Control']='public, max-age=3600'
    return response
