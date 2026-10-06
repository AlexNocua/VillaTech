from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.http import FileResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from functools import wraps
from pathlib import Path
from .models import Entry, DevelopmentProject, ProjectScreenshot
from .forms import SaleForm, OrderForm, QuotationForm, ExpenseForm, ProductForm, VariantForm, CalculatorForm, DevelopmentForm
from .pricing import calculate

def staff_only(view):
    @wraps(view)
    @login_required
    @never_cache
    def guarded(request,*args,**kwargs):
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied
        return view(request,*args,**kwargs)
    return guarded

@staff_only
def dashboard(request):
    entries = Entry.objects.all()
    totals = {kind:entries.filter(kind=kind).aggregate(total=Sum('amount'))['total'] or 0 for kind in ['sale','expense']}
    return render(request,'management/dashboard.html',{'entries':entries[:50],'sales':totals['sale'],'expenses':totals['expense'],'balance':totals['sale']-totals['expense'],'quotes':entries.filter(kind='quote').count(),'pending':entries.filter(kind='order').exclude(status__in=['delivered','cancelled','sold']).count(),'grams':entries.filter(kind__in=['sale','order']).exclude(status='cancelled').aggregate(total=Sum('filament_g'))['total'] or 0})

from django.db import transaction
from .forms import QuoteFormSet, CategoryForm, PrinterForm
from .models import PrinterProfile
from .quotation import build_quote
from django.http import HttpResponse

@staff_only
def entry_form(request,kind,pk=None):
    if kind not in dict(Entry.KIND): raise PermissionDenied
    instance = get_object_or_404(Entry,pk=pk,kind=kind) if pk else Entry(kind=kind,created_by=request.user)
    form_class={"sale":SaleForm,"order":OrderForm,"quote":QuotationForm,"expense":ExpenseForm}[kind]
    form=form_class(request.POST or None,request.FILES or None,instance=instance)
    items=QuoteFormSet(request.POST or None,request.FILES or None,instance=instance,prefix='items') if kind in ('order','quote') else None

    if request.method=='POST':
        valid=form.is_valid()
        if items is not None:valid=items.is_valid() and valid
        if valid:
            with transaction.atomic():
                entry=form.save(commit=False);entry.kind=kind
                if kind == "quote": entry.status = "quoted"
                if not pk:entry.created_by=request.user
                entry.amount=entry.amount or 0;entry.save()
                if items is not None:
                    items.instance=entry;items.save()
                    from django.core.files.base import ContentFile
                    for item in entry.items.select_related('variant').all():
                        if not item.image and item.variant_id and item.variant.image:
                            with item.variant.image.open('rb') as original:
                                item.image.save('referencia'+Path(item.variant.image.name).suffix,ContentFile(original.read()),save=True)
                    if entry.items.exists():
                        entry.amount=sum((item.total for item in entry.items.all()),0);entry.save(update_fields=['amount','updated_at'])
            if kind in ('order','quote'):
                from django.core.files.base import ContentFile
                old_pdf=entry.quotation_pdf.name
                entry.quotation_pdf.save(f'cotizacion-{entry.pk}.pdf',ContentFile(build_quote(entry)),save=True)
                if old_pdf and old_pdf!=entry.quotation_pdf.name:entry.quotation_pdf.storage.delete(old_pdf)
            messages.success(request,'Cotización guardada y PDF generado.' if kind in ('order','quote') else 'Venta registrada como vendida.' if kind=='sale' else 'Gasto registrado.')
            return redirect('management:quote_detail',pk=entry.pk) if kind in ('order','quote') else redirect('management:dashboard')
    profile=PrinterProfile.objects.filter(name='Creality K1C').first() or PrinterProfile.objects.first()
    cost_initial={'energy_mode':'rated','printer':profile.pk,'printer_price':profile.purchase_price,'useful_hours':profile.useful_hours,'maintenance_hour':profile.maintenance_hour} if profile else {}
    return render(request,'management/form.html',{'form':form,'items':items,'kind':kind,'title':dict(Entry.KIND)[kind],'cost_form':CalculatorForm(initial=cost_initial) if items is not None else None,'profiles_data':list(PrinterProfile.objects.values('id','rated_watts','average_watts','purchase_price','useful_hours','maintenance_hour'))})

@staff_only
def catalog_form(request,variant=False):
    cls=VariantForm if variant else ProductForm
    form=cls(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        form.save();messages.success(request,'Catálogo actualizado.');return redirect('management:dashboard')
    return render(request,'management/form.html',{'form':form,'title':'Nueva variante por tamaño' if variant else 'Nuevo producto'})

@staff_only
def calculator(request):
    profile=PrinterProfile.objects.filter(pk=request.GET.get('profile')).first() if request.GET.get('profile','').isdigit() else None
    if profile is None:profile=PrinterProfile.objects.filter(name='Creality K1C').first() or PrinterProfile.objects.first()
    initial={'energy_mode':'rated'}
    if profile:initial={'energy_mode':'rated','printer':profile.pk,'printer_price':profile.purchase_price,'useful_hours':profile.useful_hours,'maintenance_hour':profile.maintenance_hour,'watts':profile.average_watts}
    form=CalculatorForm(request.POST or None,initial=initial);result=None
    if request.method=='POST' and form.is_valid():result=calculate(form.cleaned_data)
    return render(request,'management/calculator.html',{'form':form,'result':result,'profiles':PrinterProfile.objects.all(),'profile':profile,'profiles_data':list(PrinterProfile.objects.values('id','rated_watts','average_watts','purchase_price','useful_hours','maintenance_hour'))})

@staff_only
def image(request,pk):
    entry=get_object_or_404(Entry,pk=pk)
    if not entry.image: raise PermissionDenied
    from PIL import Image
    stream=entry.image.open('rb')
    try:
        mime=Image.MIME[Image.open(stream).format]
        if mime not in ('image/png','image/jpeg','image/webp'): raise PermissionDenied
        stream.seek(0)
    except Exception:
        stream.close();raise PermissionDenied
    response=FileResponse(stream,content_type=mime)
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff';return response


@staff_only
def categories(request,pk=None):
    from apps.landing.models import CategoryProduct
    instance=get_object_or_404(CategoryProduct,pk=pk) if pk else None
    form=CategoryForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():form.save();return redirect('management:categories')
    return render(request,'management/categories.html',{'form':form,'categories':CategoryProduct.objects.all()})

@staff_only
def products(request,pk=None):
    from apps.landing.models import Product
    if pk is not None:
        instance=get_object_or_404(Product,pk=pk)
        form=ProductForm(request.POST or None,instance=instance)
        if request.method=='POST' and form.is_valid():form.save();return redirect('management:products')
        return render(request,'management/form.html',{'form':form,'title':'Editar producto interno / publicación'})
    return render(request,'management/products.html',{'products':Product.objects.select_related('mtm_category').all()})

@staff_only
def printers(request,pk=None):
    instance=get_object_or_404(PrinterProfile,pk=pk) if pk else None
    form=PrinterForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():form.save();return redirect('management:printers')
    return render(request,'management/printers.html',{'form':form,'profiles':PrinterProfile.objects.all()})

@staff_only
def quote_detail(request,pk):
    order=get_object_or_404(Entry,pk=pk,kind__in=['quote','order','sale'])
    return render(request,'management/quote.html',{'order':order})

@staff_only
@xframe_options_sameorigin
def quote_pdf(request,pk):
    order=get_object_or_404(Entry,pk=pk,kind__in=['quote','order','sale'])
    if order.status == 'draft':
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest('Completa la cotización antes de generar el PDF.')
    response=FileResponse(order.quotation_pdf.open('rb'),content_type='application/pdf') if order.quotation_pdf else HttpResponse(build_quote(order),content_type='application/pdf')
    response['Content-Disposition']=f'inline; filename="VillaTech-cotizacion-{order.pk}.pdf"'
    response['Cache-Control']='private, no-store';return response


@staff_only
@require_POST
def transition(request,pk,target):
    allowed={('quote','order'),('order','sale')}
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk)
        if (entry.kind,target) not in allowed or entry.status in ('cancelled','draft'):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest('Este registro ya cambió de estado o la transición no es válida.')
        entry.kind=target
        entry.status='pending' if target=='order' else 'sold'
        entry.save()
    messages.success(request,'Pedido confirmado.' if target=='order' else 'Venta registrada como vendida. El ingreso se cuenta una sola vez.')
    return redirect('management:quote_detail',pk=entry.pk)

@staff_only
@require_POST
def estimate(request):
    from django.http import JsonResponse
    form=CalculatorForm(request.POST)
    if not form.is_valid():return JsonResponse({'errors':{form.fields[key].label:[str(e) for e in value] for key,value in form.errors.items()}},status=400)
    return JsonResponse({'result':calculate(form.cleaned_data)})

@staff_only
def development(request,pk=None):
    project=get_object_or_404(DevelopmentProject,pk=pk) if pk else None
    form=DevelopmentForm(request.POST or None,instance=project)
    if request.method=='POST':
        valid=form.is_valid();uploads=request.FILES.getlist('screenshots')
        if len(uploads)>6:
            form.add_error(None,'Puedes agregar hasta 6 imágenes por envío.');valid=False
        from apps.landing.validators import validate_image
        from django.core.exceptions import ValidationError
        for uploaded in uploads:
            try:validate_image(uploaded);uploaded.seek(0)
            except ValidationError as error:form.add_error(None,error);valid=False
        if valid:
            with transaction.atomic():
                project=form.save(commit=False)
                if not pk:project.created_by=request.user
                project.save()
                for uploaded in uploads:ProjectScreenshot.objects.create(project=project,image=uploaded)
            messages.success(request,'Proyecto y capturas guardados.')
            return redirect('management:development')
    projects=DevelopmentProject.objects.prefetch_related('screenshots').all()
    return render(request,'management/development.html',{'projects':projects,'form':form,'editing':project})

@staff_only
def screenshot(request,pk):
    from PIL import Image
    shot=get_object_or_404(ProjectScreenshot,pk=pk)
    stream=shot.image.open('rb')
    try:
        mime=Image.MIME[Image.open(stream).format]
        if mime not in ('image/png','image/jpeg','image/webp'):raise PermissionDenied
        stream.seek(0)
    except Exception:
        stream.close();raise PermissionDenied
    response=FileResponse(stream,content_type=mime)
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff'
    return response


@staff_only
def entry_list(request, section='orders'):
    entries = Entry.objects.select_related('contact')
    if section == 'quotes':
        entries = entries.filter(kind='quote')
        statuses = [choice for choice in Entry.STATUS if choice[0] in ('draft','quoted','cancelled')]
    else:
        # Incoming web drafts remain visible until priced and confirmed.
        entries = entries.filter(Q(kind='order') | Q(kind='quote',source='web'))
        statuses = [choice for choice in Entry.STATUS if choice[0] != 'sold']
    status = request.GET.get('status','')
    source = request.GET.get('source','')
    query = request.GET.get('q','').strip()[:150]
    if status in dict(statuses): entries = entries.filter(status=status)
    if source in ('web','manual'): entries = entries.filter(source=source)
    if query:
        entries = entries.filter(Q(title__icontains=query) | Q(customer__icontains=query) | Q(customer_email__icontains=query))
    page = Paginator(entries,25).get_page(request.GET.get('page'))
    params = request.GET.copy(); params.pop('page',None)
    return render(request,'management/entries.html',{'page':page,'section':section,'statuses':statuses,
        'status':status,'source':source,'query':query,'filters_query':params.urlencode()})

@staff_only
def contact_attachment(request,pk):
    from apps.landing.models import ContactAttachment
    attachment = get_object_or_404(ContactAttachment,pk=pk)
    response = FileResponse(attachment.file.open('rb'),as_attachment=True,filename=Path(attachment.file.name).name,
        content_type='application/octet-stream')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response

@staff_only
@require_POST
def retry_notifications(request,pk):
    entry = get_object_or_404(Entry,pk=pk,source='web',contact__isnull=False)
    from apps.landing.notifications import safely_dispatch
    safely_dispatch(entry.contact_id)
    messages.info(request,'Reintento realizado. Revisa el estado de cada correo.')
    return redirect('management:quote_detail',pk=pk)


@staff_only
def legacy_contact_file(request,pk):
    from apps.landing.models import Contact
    from django.http import Http404
    contact = get_object_or_404(Contact,pk=pk)
    if not contact.file: raise Http404
    response = FileResponse(contact.file.open('rb'),as_attachment=True,
        filename=Path(contact.file.name).name,content_type='application/octet-stream')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
