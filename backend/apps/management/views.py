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
from .models import Entry, DevelopmentProject, ProjectScreenshot, Payment
from .forms import SaleForm, OrderForm, QuotationForm, ExpenseForm, ProductForm, VariantForm, CalculatorForm, DevelopmentForm
from .pricing import calculate
from .workflow import active_orders, estimate_delivery, approve_order, queue_order_email, schedule_dispatch
from .forms import ApprovalForm, DeliveryForm
from django.utils import timezone
from datetime import timedelta

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
    from .quotations import expire_quotes
    expire_quotes()
    entries = Entry.objects.all()
    commercial = entries.filter(kind__in=['sale','order']).exclude(status='cancelled')
    totals = {'sale': commercial.aggregate(total=Sum('amount'))['total'] or 0, 'expense': entries.filter(kind='expense').aggregate(total=Sum('amount'))['total'] or 0}
    collected = commercial.aggregate(total=Sum('paid_amount'))['total'] or 0
    today = timezone.localdate()
    active = active_orders()
    agenda = active.filter(estimated_delivery_date__lte=today+timedelta(days=3)).order_by('estimated_delivery_date')[:12]
    return render(request,'management/dashboard.html',{'entries':entries[:12],'agenda':agenda,
        'overdue':active.filter(estimated_delivery_date__lt=today).count(),
        'due_today':active.filter(estimated_delivery_date=today).count(),
        'upcoming':active.filter(estimated_delivery_date__gt=today,estimated_delivery_date__lte=today+timedelta(days=3)).count(),
        'undated':active.filter(estimated_delivery_date__isnull=True).count(),
        'failed_emails':__import__('apps.management.models',fromlist=['OperationalEmail']).OperationalEmail.objects.filter(status__in=['pending','failed']).count(),
        'collected':collected,'receivable':totals['sale']-collected,'cash_balance':collected-totals['expense'],'sales':totals['sale'],'expenses':totals['expense'],'balance':totals['sale']-totals['expense'],'quotes':entries.filter(kind='quote').count(),'pending':active.count(),'grams':commercial.aggregate(total=Sum('filament_g'))['total'] or 0})

from django.db import transaction
from .forms import QuoteFormSet, CategoryForm, PrinterForm
from .models import PrinterProfile
from .quotation import build_quote
from django.http import HttpResponse

@staff_only
def entry_form(request,kind,pk=None):
    if kind not in dict(Entry.KIND): raise PermissionDenied
    instance = get_object_or_404(Entry,pk=pk,kind=kind) if pk else Entry(kind=kind,created_by=request.user)
    if kind in ('quote','order') and pk and instance.status in ('sent','expired'):
        from .commerce import edit
        return edit(request,pk)
    old_status, old_date = instance.status, instance.estimated_delivery_date
    form_class={"sale":SaleForm,"order":OrderForm,"quote":QuotationForm,"expense":ExpenseForm}[kind]
    form=form_class(request.POST or None,request.FILES or None,instance=instance)
    items=QuoteFormSet(request.POST or None,request.FILES or None,instance=instance,prefix='items') if kind in ('order','quote') else None

    if request.method=='POST':
        valid=form.is_valid()
        if items is not None:valid=items.is_valid() and valid
        if valid and items is not None:
            active = [f.cleaned_data for f in items.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
            if active and sum(d.get('quantity',0)*d.get('unit_price',0) for d in active) < instance.paid_amount:
                form.add_error(None,'El total de productos no puede ser menor que los abonos registrados.'); valid=False
        if valid:
            with transaction.atomic():
                entry=form.save(commit=False);entry.kind=kind
                if pk:
                    current = Entry.objects.select_for_update().get(pk=pk)
                    if current.kind != kind:
                        messages.error(request, 'El registro cambió de etapa. Revisa su ficha antes de editar.')
                        return redirect('management:quote_detail', pk=pk)
                    # Preserve payments and approval recorded while the editor was open.
                    entry.paid_amount, entry.approved_at = current.paid_amount,current.approved_at
                    effective = entry.amount
                    if items is not None and active:
                        effective = sum(d.get('quantity',0)*d.get('unit_price',0) for d in active)
                    if effective < current.paid_amount or (entry.status == 'cancelled' and current.paid_amount):
                        form.add_error(None,'Los abonos cambiaron mientras editabas. Revisa el total y el estado antes de guardar.')
                        return render(request,'management/form.html',{'form':form,'items':items,'kind':kind,'title':dict(Entry.KIND)[kind]})
                if kind == "quote": entry.status = "quoted"
                if not pk:entry.created_by=request.user
                entry.amount=entry.amount or 0
                entry.unit_price=entry.amount;entry.quantity=1;entry.unit_filament_g=entry.filament_g;entry.unit_print_hours=entry.print_hours
                entry.save()
                if items is not None:
                    items.instance=entry;items.save()
                    from django.core.files.base import ContentFile
                    for item in entry.items.select_related('variant').all():
                        if not item.image and item.variant_id and item.variant.image:
                            with item.variant.image.open('rb') as original:
                                item.image.save('referencia'+Path(item.variant.image.name).suffix,ContentFile(original.read()),save=True)
                    if entry.items.exists():
                        entry.amount=sum((item.total for item in entry.items.all()),0)
                        if entry.amount < entry.paid_amount:
                            from django.core.exceptions import ValidationError
                            raise ValidationError('El total de productos no puede ser menor que los abonos registrados.')
                        entry.save(update_fields=['amount','updated_at'])
                if kind == 'order' and entry.status == 'delivered':
                    from .workflow import complete_delivery
                    complete_delivery(entry, request.user)
                elif kind == 'order':
                    first = entry.approved_at is None
                    schedule_dispatch(approve_order(entry))
                    if not first and (old_status != entry.status or old_date != entry.estimated_delivery_date):
                        event = entry.status if entry.status in ('printing','ready','delivered','cancelled') else 'updated'
                        schedule_dispatch(queue_order_email(entry,event))
            if kind in ('order','quote'):
                from django.core.files.base import ContentFile
                old_pdf=entry.quotation_pdf.name
                entry.quotation_pdf.save(f'cotizacion-{entry.pk}.pdf',ContentFile(build_quote(entry)),save=True)
                if old_pdf and old_pdf!=entry.quotation_pdf.name:entry.quotation_pdf.storage.delete(old_pdf)
            messages.success(request,'Pedido guardado. Consulta fecha y correos en su ficha.' if kind=='order' else 'Cotización guardada y PDF generado.' if kind=='quote' else 'Venta registrada como vendida.' if kind=='sale' else 'Gasto registrado.')
            return redirect('management:quote_detail',pk=entry.pk) if kind in ('order','quote','sale') else redirect('management:dashboard')
    profile=PrinterProfile.objects.filter(name='Creality K1C').first() or PrinterProfile.objects.first()
    cost_initial={'energy_mode':'rated','printer':profile.pk,'printer_price':profile.purchase_price,'useful_hours':profile.useful_hours,'maintenance_hour':profile.maintenance_hour} if profile else {}
    return render(request,'management/form.html',{'form':form,'items':items,'kind':kind,'title':dict(Entry.KIND)[kind],'cost_form':CalculatorForm(initial=cost_initial) if items is not None else None,'profiles_data':list(PrinterProfile.objects.values('id','rated_watts','average_watts','purchase_price','useful_hours','maintenance_hour'))})

@staff_only
def catalog_form(request,variant=False):
    cls=VariantForm if variant else ProductForm
    form=cls(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        form.save();messages.success(request,'Catálogo actualizado.');return redirect('management:variants' if variant else 'management:products')
    return render(request,'management/form.html',{'form':form,'title':'Nueva variante por tamaño' if variant else 'Nuevo producto'})

@staff_only
def expenses(request):
    query = request.GET.get('q','').strip()[:150]
    entries = Entry.objects.filter(kind='expense')
    if query:
        entries = entries.filter(title__icontains=query)
    return render(request,'management/expenses.html',{'page':Paginator(entries,25).get_page(request.GET.get('page')),'query':query})

@staff_only
def variants(request,pk=None):
    from apps.landing.models import ProductVariant
    if pk:
        instance = get_object_or_404(ProductVariant,pk=pk)
        form = VariantForm(request.POST or None,request.FILES or None,instance=instance)
        if request.method == 'POST' and form.is_valid():
            form.save()
            return redirect('management:variants')
        return render(request,'management/form.html',{'form':form,'title':'Editar tamaño y precio'})
    return render(request,'management/variants.html',{'variants':ProductVariant.objects.select_related('product').all()})

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
        form=ProductForm(request.POST or None,request.FILES or None,instance=instance)
        if request.method=='POST' and form.is_valid():form.save();return redirect('management:products')
        return render(request,'management/form.html',{'form':form,'title':'Editar producto interno / publicación'})
    query = request.GET.get('q','').strip()[:150]
    products = Product.objects.select_related('mtm_category').all()
    if query:
        products = products.filter(Q(name__icontains=query)|Q(mtm_category__category_name__icontains=query))
    if request.GET.get('stock') == 'empty':
        products = products.filter(stock=0,is_active=True)
    page = Paginator(products.order_by('name','pk'),25).get_page(request.GET.get('page'))
    return render(request,'management/products.html',{'products':page,'page':page,'query':query,'stock_filter':request.GET.get('stock',''),
        'stock_movements':__import__('apps.management.models',fromlist=['StockMovement']).StockMovement.objects.select_related('product','created_by')[:50]})

@staff_only
def printers(request,pk=None):
    instance=get_object_or_404(PrinterProfile,pk=pk) if pk else None
    form=PrinterForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():form.save();return redirect('management:printers')
    return render(request,'management/printers.html',{'form':form,'profiles':PrinterProfile.objects.all()})

@staff_only
def quote_detail(request,pk):
    from .commerce import detail
    return detail(request,pk)


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
        if target == 'order':
            from .quotations import confirm_quotation
            from django.core.exceptions import ValidationError
            form=ApprovalForm(request.POST)
            if not form.is_valid():
                messages.error(request,'Revisa la fecha de entrega.');return redirect('management:quote_detail',pk=pk)
            try:confirm_quotation(entry,'internal','Confirmación registrada en gestión.',request.user,form.cleaned_data['estimated_delivery_date'])
            except ValidationError as error:
                messages.error(request,' '.join(error.messages));return redirect('management:quote_detail',pk=pk)
            messages.success(request,'Pedido confirmado.');return redirect('management:quote_detail',pk=pk)
        elif entry.status != 'delivered':
            messages.error(request,'Marca el pedido como entregado antes de archivarlo como venta.')
            return redirect('management:quote_detail',pk=pk)
        if target == 'sale':
            from .workflow import complete_delivery
            complete_delivery(entry, request.user)
            messages.success(request, 'Entrega cerrada como venta y saldo liquidado.')
            return redirect('management:quote_detail', pk=entry.pk)
        entry.kind=target
        entry.status='pending' if target=='order' else 'sold'
        entry.save()
        if target == 'order':
            schedule_dispatch(approve_order(entry))
    messages.success(request,'Pedido confirmado.' if target=='order' else 'Venta registrada como vendida. El ingreso se cuenta una sola vez.')
    return redirect('management:quote_detail',pk=entry.pk)

@staff_only
@require_POST
def update_delivery(request,pk):
    with transaction.atomic():
        entry = get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind__in=['order','sale'])
        if entry.kind == 'sale':
            messages.info(request, 'Esta entrega ya está cerrada como venta.')
            return redirect('management:quote_detail', pk=pk)
        form = DeliveryForm(request.POST)
        if not form.is_valid():
            messages.error(request,'Revisa el estado y la fecha de entrega.')
        elif form.cleaned_data['status'] == 'delivered' and entry.status != 'cancelled':
            from .workflow import complete_delivery
            entry.estimated_delivery_date = form.cleaned_data['estimated_delivery_date'] or entry.estimated_delivery_date
            complete_delivery(entry, request.user)
            messages.success(request, 'Entregado: venta registrada y saldo liquidado automáticamente.')
        elif entry.status in ('delivered','cancelled'):
            messages.error(request,'El pedido está cerrado. Conserva su historial y crea otro registro si corresponde.')
        elif form.cleaned_data['status'] == 'cancelled' and entry.paid_amount:
            messages.error(request,'El pedido tiene abonos. Concilia los pagos antes de cancelar.')
        else:
            date = form.cleaned_data['estimated_delivery_date'] or entry.estimated_delivery_date or estimate_delivery(entry)
            status = form.cleaned_data['status']
            if (date,status) != (entry.estimated_delivery_date,entry.status) or not entry.approved_at:
                first = entry.approved_at is None
                entry.estimated_delivery_date,entry.status = date,status
                from .models import EntryActivity
                EntryActivity.objects.create(entry=entry,label=dict(Entry.STATUS)[status],note=f'Entrega estimada: {date:%d/%m/%Y}',actor=request.user)
                entry.save(update_fields=['estimated_delivery_date','status','updated_at'])
                if first and status in ('pending','printing','ready'):
                    schedule_dispatch(approve_order(entry))
                else:
                    schedule_dispatch(queue_order_email(entry,status if status in ('printing','ready','delivered','cancelled') else 'updated'))
            messages.success(request,'Seguimiento guardado. Si el cliente tiene correo, consulta el aviso en esta ficha.')
    return redirect('management:quote_detail',pk=pk)

@staff_only
@require_POST
def retry_order_notifications(request,pk):
    from .workflow import safely_dispatch
    entry = get_object_or_404(Entry,pk=pk,kind__in=['order','sale'])
    for message in entry.emails.filter(status__in=['pending','failed']):
        safely_dispatch(message.pk)
    messages.info(request,'Reintento realizado. Consulta el estado del correo.')
    return redirect('management:quote_detail',pk=pk)

@staff_only
def email_list(request):
    from .models import OperationalEmail
    emails = OperationalEmail.objects.select_related('entry')
    status = request.GET.get('status','')
    if status in ('pending','failed','sent','skipped'):
        emails = emails.filter(status=status)
    return render(request,'management/emails.html',{'page':Paginator(emails,25).get_page(request.GET.get('page')),'status':status})

@staff_only
@require_POST
def retry_email(request,pk):
    from .models import OperationalEmail
    from .workflow import safely_dispatch
    message = get_object_or_404(OperationalEmail,pk=pk)
    safely_dispatch(message.pk)
    messages.info(request,'Reintento realizado. Consulta el estado actualizado.')
    return redirect('management:email_list')

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
        statuses = [choice for choice in Entry.STATUS if choice[0] in ('draft','quoted','sent','expired','cancelled')]
    elif section == 'sales':
        entries = entries.filter(kind__in=['order','sale']).exclude(status='cancelled')
        statuses = Entry.STATUS
    else:
        entries = entries.filter(kind='order')
        statuses = [choice for choice in Entry.STATUS if choice[0] != 'sold']
    status = request.GET.get('status','')
    source = request.GET.get('source','')
    query = request.GET.get('q','').strip()[:150]
    due = request.GET.get('due','')
    today = timezone.localdate()
    if due in ('overdue','today','upcoming','undated'):
        entries = entries.filter(kind='order',status__in=['pending','printing','ready'])
        if due == 'overdue': entries = entries.filter(estimated_delivery_date__lt=today)
        elif due == 'today': entries = entries.filter(estimated_delivery_date=today)
        elif due == 'upcoming': entries = entries.filter(estimated_delivery_date__gt=today,estimated_delivery_date__lte=today+timedelta(days=3))
        else: entries = entries.filter(estimated_delivery_date__isnull=True)
    if request.GET.get('balance') == 'pending':
        from django.db.models import F
        entries = entries.filter(kind__in=['sale','order'],amount__gt=F('paid_amount')).exclude(status='cancelled')
    if status in dict(statuses): entries = entries.filter(status=status)
    if source in ('web','manual'): entries = entries.filter(source=source)
    if query:
        entries = entries.filter(Q(title__icontains=query) | Q(customer__icontains=query) | Q(customer_email__icontains=query))
    page = Paginator(entries,25).get_page(request.GET.get('page'))
    params = request.GET.copy(); params.pop('page',None)
    return render(request,'management/entries.html',{'page':page,'section':section,'statuses':statuses,
        'status':status,'due':due,'balance_filter':request.GET.get('balance',''),'products':__import__('apps.landing.models',fromlist=['Product']).Product.objects.filter(is_active=True),'source':source,'query':query,'filters_query':params.urlencode()})

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

@staff_only
@require_POST
def record_payment(request,pk):
    from decimal import Decimal, InvalidOperation
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind__in=['order','sale'])
        try:
            amount=Decimal(request.POST.get('payment',''))
            if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal('0.01')) or amount > entry.outstanding or entry.status == 'cancelled':
                raise ValueError
        except (InvalidOperation,ValueError):
            messages.error(request,'Introduce un abono positivo, con máximo dos decimales y sin superar el saldo pendiente.')
        else:
            Payment.objects.create(entry=entry,amount=amount,created_by=request.user)
            entry.paid_amount += amount
            from .models import EntryActivity
            EntryActivity.objects.create(entry=entry,label='Abono registrado',note=f'{amount} COP',actor=request.user)
            entry.save(update_fields=['paid_amount','updated_at'])
            messages.success(request,'Abono registrado. El total vendido no cambia.')
    return redirect('management:quote_detail',pk=pk)

@staff_only
@require_POST
def enable_product(request,pk):
    from apps.landing.models import Product
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind__in=['order','sale','quote'])
        if not entry.reference_product_id:
            selected=request.POST.get('product','')
            if selected:
                entry.reference_product=get_object_or_404(Product,pk=selected,is_active=True)
                entry.product_category=entry.reference_product.mtm_category
            elif entry.product_category_id:
                entry.reference_product=Product.objects.create(name=entry.title,description=entry.description,
                    mtm_category=entry.product_category,price=entry.amount,stock=0,is_public=False)
            else:
                messages.error(request,'Asigna una categoría al registro o selecciona un producto existente.')
                return redirect('management:edit',kind=entry.kind,pk=pk)
            entry.save(update_fields=['reference_product','product_category','updated_at'])
        messages.success(request,'Producto vinculado al registro. Revisa su precio unitario y existencias en Inventario.')
    return redirect('management:product_edit',pk=entry.reference_product_id)

@staff_only
@require_POST
def adjust_stock(request,pk):
    from apps.landing.models import Product
    from .models import StockMovement
    with transaction.atomic():
        product=get_object_or_404(Product.objects.select_for_update(),pk=pk)
        try:
            quantity=int(request.POST.get('quantity',''))
            reason=request.POST.get('reason','').strip()
            if not quantity or abs(quantity)>1000000 or product.stock+quantity<0 or not reason or len(reason)>150:
                raise ValueError
        except (ValueError,TypeError):
            messages.error(request,'Introduce unidades enteras, un motivo y un ajuste que no deje existencias negativas.')
        else:
            product.stock+=quantity
            product.save(update_fields=['stock','updated_at'])
            StockMovement.objects.create(product=product,quantity=quantity,reason=reason,created_by=request.user)
            messages.success(request,'Existencias ajustadas y movimiento registrado.')
    return redirect('management:products')
