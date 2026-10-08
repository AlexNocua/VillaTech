import os

from django.shortcuts import render, redirect
from django.contrib import messages

from .models import Product, Contact, CategoryProduct

# ruta base del proyecto
from django.conf import settings

BASE_DIR = settings.BASE_DIR_TEMPLATES


# Create your views here.
def recuperar_productos(request):

    # Logica para la busqueda de productos en la base de datos
    data = Product.objects.filter(is_active=True, is_public=True, mtm_category__is_active=True).select_related("mtm_category").prefetch_related("fk_tags", "variants")

    context = {"catalog_products": data,"catalog_categories":CategoryProduct.objects.filter(is_active=True)}

    return render(request, "landing/pages/landing.html", context)




from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import ValidationError
from .contact_forms import ContactForm, validate_reference
from .models import ContactAttachment

@require_POST
def contact_form_action(request):
    key = 'contact:' + request.META.get('REMOTE_ADDR','unknown')
    count=cache.get(key,0)
    if count>=5:
        messages.error(request,'Demasiadas solicitudes. Intenta nuevamente en unos minutos.')
        return redirect('landing:recuperar_productos')
    cache.set(key,count+1,600)
    form=ContactForm(request.POST)
    files=request.FILES.getlist('reference_files')
    try:
        if not form.is_valid(): raise ValidationError('Revisa los campos y acepta el aviso de privacidad.')
        if len(files)>5 or sum(f.size for f in files)>20*1024*1024:
            raise ValidationError('Máximo 5 archivos y 20 MB en total.')
        for file in files: validate_reference(file)
        data=form.cleaned_data
        phone=''.join(c for c in data['phone'] if c.isdigit())
        with transaction.atomic():
            contact=Contact.objects.create(client_name=data['name'],telephone=int(phone),email=data['email'],service=data['service'],message=data['message'],file='')
            for file in files: ContactAttachment.objects.create(contact=contact,file=file)
            from apps.management.models import Entry
            from .notifications import queue_contact_emails, safely_dispatch
            entry = Entry.objects.create(kind='quote', status='draft', source='web', contact=contact,
                title=f"Solicitud web · {data['service']}", description=data['message'],
                customer=data['name'][:150], customer_email=data['email'], customer_phone=data['phone'], amount=0)
            queue_contact_emails(contact, entry)
            transaction.on_commit(lambda: safely_dispatch(contact.pk))
    except ValidationError as error:
        messages.error(request,' '.join(error.messages))
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Error al guardar solicitud y archivos de referencia')
        messages.error(request,'No pudimos guardar tu solicitud. Intenta nuevamente.')
    else:
        messages.success(request,'Recibimos tu solicitud. Te contactaremos para revisar tu proyecto.')
    return redirect('landing:recuperar_productos')
