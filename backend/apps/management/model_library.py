from pathlib import Path
import logging
from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse,FileResponse,Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from .models import PrintingModel
from .views import staff_only
from apps.landing.models import Product,ContactAttachment
from .mesh_preview import mesh_preview,solid_mesh_preview

class ModelForm(forms.ModelForm):
    class Meta:
        model=PrintingModel
        fields=['title','description','file']
        widgets={'file':forms.FileInput(attrs={'accept':'.stl,.3mf','data-model-file':''})}
    def clean_file(self):
        file=self.cleaned_data['file']
        if Path(file.name).suffix.lower() not in ('.stl','.3mf'):raise forms.ValidationError('Carga un STL o 3MF de hasta 100 MB.')
        return file

@staff_only
def library(request):
    form=ModelForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        asset=form.save(commit=False)
        asset.created_by=request.user
        asset.original_name=Path(form.cleaned_data['file'].name).name[:255]
        try:
            # Geometry is deliberately not parsed while saving an upload.
            with transaction.atomic():
                asset.save()
        except Exception:
            logging.getLogger(__name__).exception('No se pudo guardar modelo 3D (usuario=%s)',request.user.pk)
            if asset.file and asset.file._committed:
                try: asset.file.storage.delete(asset.file.name)
                except Exception: logging.getLogger(__name__).exception('No se pudo retirar archivo incompleto de modelo')
            form.add_error(None,'No pudimos guardar el modelo. Revisa el almacenamiento disponible e intenta de nuevo. Los detalles quedaron en los logs; vuelve a seleccionar el archivo.')
        else:
            return redirect('management:model_library')
    rows=[]
    query=request.GET.get('q','').strip()[:150]
    def row(kind,obj,title,name):
        if not query or query.casefold() in (title+' '+name).casefold():
            rows.append({'title':title,'name':name,'source':{'asset':'Biblioteca','product':'Producto','reference':'Cliente'}[kind],
                'preview':reverse('management:model_preview',args=[kind,obj.pk]),'download':reverse('management:model_download',args=[kind,obj.pk])})
    for obj in PrintingModel.objects.all():row('asset',obj,obj.title,obj.original_name)
    for obj in Product.objects.exclude(print_model=''):
        row('product',obj,obj.name,obj.print_model_original_name or Path(obj.print_model.name).name)
    for obj in ContactAttachment.objects.filter(file__iregex=r'\.(stl|3mf)$').select_related('contact'):
        row('reference',obj,'Solicitud #'+str(obj.contact_id)+' · '+obj.contact.client_name,obj.display_name)
    from django.core.paginator import Paginator
    return render(request,'management/model_library.html',{'form':form,'page':Paginator(rows,30).get_page(request.GET.get('page')),'query':query})

def model_file(kind,pk):
    if kind=='asset':obj=get_object_or_404(PrintingModel,pk=pk);return obj.file,obj.original_name
    if kind=='product':obj=get_object_or_404(Product,pk=pk);return obj.print_model,obj.print_model_original_name
    if kind=='reference':obj=get_object_or_404(ContactAttachment,pk=pk);return obj.file,obj.display_name
    raise Http404

@staff_only
def preview(request,kind,pk):
    file,name=model_file(kind,pk)
    if not file:raise Http404
    try:
        if 'application/octet-stream' in request.headers.get('Accept',''):
            response=FileResponse(solid_mesh_preview(file),content_type='application/octet-stream')
            response['Cache-Control']='private, no-store'
            response['X-Content-Type-Options']='nosniff'
            return response
        data=mesh_preview(file)
    except ValidationError as error:return JsonResponse({'error':' '.join(error.messages)},status=422)
    except Exception as error:
        logging.getLogger(__name__).warning('No se pudo preparar vista de modelo: %s',type(error).__name__)
        return JsonResponse({'error':'Este archivo no se pudo interpretar. Descarga el original para abrirlo en tu laminador.'},status=422)
    response=JsonResponse(data);response['Cache-Control']='private, no-store';return response

@staff_only
def download(request,kind,pk):
    file,name=model_file(kind,pk)
    if not file:raise Http404
    response=FileResponse(file.open('rb'),as_attachment=True,filename=name or Path(file.name).name,content_type='application/octet-stream')
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff';return response
