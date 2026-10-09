import os

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from .models import Product, Contact, CategoryProduct

# ruta base del proyecto
from django.conf import settings

BASE_DIR = settings.BASE_DIR_TEMPLATES


# Create your views here.
def recuperar_productos(request, contact_form=None, contact_error=None, status=200):

    # Logica para la busqueda de productos en la base de datos
    data = Product.objects.filter(is_active=True, is_public=True, mtm_category__is_active=True).select_related("mtm_category").prefetch_related("fk_tags", "variants")

    context = {"catalog_products": data,"catalog_categories":CategoryProduct.objects.filter(is_active=True)}

    context.update(contact_form=contact_form, contact_error=contact_error)
    return render(request, "landing/pages/landing.html", context, status=status)




from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import ValidationError
from .contact_forms import ContactForm, validate_reference
from .models import ContactAttachment

def contact_response(request, form, errors=None, message='', status=200):
    from django.http import JsonResponse
    if 'application/json' in request.headers.get('Accept',''):
        return JsonResponse({'ok':status == 200,'message':message,'errors':errors or {}},status=status)
    if status != 200:
        if errors and errors.get('reference_files'):
            form.add_error(None,' '.join(errors['reference_files']))
        return recuperar_productos(request,contact_form=form,contact_error=message,status=status)
    messages.success(request,message)
    return redirect(reverse('landing:recuperar_productos') + '#contacto')

@require_POST
def contact_form_action(request):
    from django.urls import reverse
    form=ContactForm(request.POST)
    files=request.FILES.getlist('reference_files')
    valid=form.is_valid()
    errors={name:[str(error) for error in values] for name,values in form.errors.items()}
    file_errors=[]
    if len(files)>5: file_errors.append('Selecciona como máximo 5 archivos.')
    if sum(f.size for f in files)>20*1024*1024: file_errors.append('Los archivos no pueden superar 20 MB en total.')
    for file in files:
        try: validate_reference(file)
        except ValidationError as error: file_errors.extend(f'{file.name}: {message}' for message in error.messages)
    if file_errors: errors['reference_files']=file_errors
    if not valid or errors:
        return contact_response(request,form,errors,'Revisa los campos indicados. Tus datos se conservan.',400)
    key='contact:' + request.META.get('REMOTE_ADDR','unknown')
    count=cache.get(key,0)
    if count>=5:
        return contact_response(request,form,message='Demasiadas solicitudes. Espera unos minutos; tus datos se conservan.',status=429)
    cache.set(key,count+1,600)
    try:
        data=form.cleaned_data
        with transaction.atomic():
            contact=Contact.objects.create(client_name=data['name'],telephone=data['phone'].strip(),email=data['email'],service=data['service'],message=data['message'],file='')
            for file in files: ContactAttachment.objects.create(contact=contact,file=file)
            from apps.management.models import Entry
            from .notifications import queue_contact_emails, safely_dispatch
            entry=Entry.objects.create(kind='quote',status='draft',source='web',contact=contact,
                title=f"Solicitud web · {data['service']}",description=data['message'],customer=data['name'][:150],
                customer_email=data['email'],customer_phone=data['phone'],amount=0)
            queue_contact_emails(contact,entry)
            transaction.on_commit(lambda:safely_dispatch(contact.pk))
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Error al guardar solicitud y archivos de referencia')
        return contact_response(request,form,message='No pudimos guardar tu solicitud por un problema interno. Tus datos se conservan para que puedas intentar nuevamente.',status=500)
    return contact_response(request,form,message='Recibimos tu solicitud. Te contactaremos para revisar tu proyecto.')
