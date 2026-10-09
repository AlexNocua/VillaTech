from decimal import Decimal
from datetime import timedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from .customer_security import customer_headers
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django import forms
from .views import staff_only
from .models import Entry, EntryActivity
from .forms import WorkflowForm, QuoteFormSet, ApprovalForm, DeliveryForm
from .quotations import expire_quotes, send_quotation, confirm_quotation, entry_from_token, renew_quotation, recalculate, approval_url
from .workflow import schedule_dispatch

class ConfirmationForm(ApprovalForm):
    channel=forms.ChoiceField(label='Confirmación recibida por',choices=[('message','Mensaje o respuesta de correo'),('internal','Aprobación en gestión')])
    note=forms.CharField(label='Referencia de la confirmación',max_length=255,required=True,
        help_text='Ejemplo: WhatsApp del cliente o respuesta de correo del 09 de octubre.')

def detail_context(entry):
    return {'order':entry,'delivery_form':DeliveryForm(initial={'estimated_delivery_date':entry.estimated_delivery_date,'status':entry.status}),'confirmation_form':ConfirmationForm(initial={'estimated_delivery_date':entry.estimated_delivery_date}),
        'share_url':approval_url(entry) if entry.kind=='quote' and entry.status=='sent' else ''}

@staff_only
def board(request):
    expire_quotes()
    entries=Entry.objects.filter(kind__in=['quote','order','sale']).prefetch_related('items')
    search=request.GET.get('q','').strip()[:150];stage=request.GET.get('stage','all')
    if search:entries=entries.filter(Q(title__icontains=search)|Q(customer__icontains=search)|Q(customer_email__icontains=search))
    stages={'quotes':Q(kind='quote',status__in=['draft','quoted']), 'awaiting':Q(kind='quote',status='sent'),
        'orders':Q(kind='order',status__in=['pending','printing','ready']),
        'completed':Q(status__in=['delivered','sold']), 'closed':Q(status__in=['expired','cancelled']),
        'receivable':Q(kind__in=['order','sale'],amount__gt=F('paid_amount'))&~Q(status='cancelled')}
    counts={key:entries.filter(value).count() for key,value in stages.items()}
    if stage in stages:entries=entries.filter(stages[stage])
    due=request.GET.get('due','')
    if due in ('overdue','today','upcoming','undated'):
        entries=entries.filter(kind='order',status__in=['pending','printing','ready'])
        today=timezone.localdate()
        if due=='overdue':entries=entries.filter(estimated_delivery_date__lt=today)
        elif due=='today':entries=entries.filter(estimated_delivery_date=today)
        elif due=='upcoming':entries=entries.filter(estimated_delivery_date__gt=today,estimated_delivery_date__lte=today+timedelta(days=3))
        else:entries=entries.filter(estimated_delivery_date__isnull=True)
    page=Paginator(entries,20).get_page(request.GET.get('page'))
    return render(request,'management/workflow_board.html',{'page':page,'stage':stage,'search':search,'counts':counts,'due':due})

@staff_only
def detail(request,pk):
    expire_quotes()
    entry=get_object_or_404(Entry.objects.prefetch_related('items','payments','activities','emails'),pk=pk,kind__in=['quote','order','sale'])
    return render(request,'management/workflow_detail.html',detail_context(entry))

@staff_only
def edit(request,pk=None):
    expire_quotes()
    entry=get_object_or_404(Entry,pk=pk,kind__in=['quote','order']) if pk else Entry(kind='quote',status='quoted',created_by=request.user)
    if entry.status in ('delivered','cancelled'):
        messages.error(request,'El registro está cerrado. Conserva su historial.');return redirect('management:workflow_detail',pk=pk)
    form=WorkflowForm(request.POST or None,request.FILES or None,instance=entry)
    items=QuoteFormSet(request.POST or None,request.FILES or None,instance=entry,prefix='items')
    if request.method=='POST':
        valid=form.is_valid();valid=items.is_valid() and valid
        if valid:
            try:
                with transaction.atomic():
                    locked=Entry.objects.select_for_update().get(pk=pk) if pk else None
                    if locked and (locked.kind!=entry.kind or locked.status!=entry.status):
                        raise ValidationError('El registro cambió mientras editabas. Abre la ficha para revisar su estado.')
                    entry=form.save(commit=False)
                    if locked:entry.paid_amount=locked.paid_amount
                    if locked and locked.status in ('sent','expired'):
                        renew_quotation(entry,request.user)
                    if entry.kind=='quote':entry.status='quoted'
                    if locked and entry.kind=='order' and not entry.estimated_delivery_date:
                        entry.estimated_delivery_date=locked.estimated_delivery_date
                    entry.quotation_pdf=''
                    entry.amount=entry.quantity*entry.unit_price
                    entry.save();items.instance=entry;items.save();recalculate(entry)
                    if locked and entry.kind=='order' and locked.estimated_delivery_date!=entry.estimated_delivery_date:
                        from .workflow import queue_order_email
                        schedule_dispatch(queue_order_email(entry,'updated'))
                    EntryActivity.objects.create(entry=entry,label='Cotización preparada' if entry.kind=='quote' else 'Detalle del pedido actualizado',actor=request.user)
                messages.success(request,'Registro guardado. Revisa el detalle y envía la cotización cuando esté lista.')
                return redirect('management:workflow_detail',pk=entry.pk)
            except ValidationError as error:
                form.add_error(None,error)
    return render(request,'management/workflow_form.html',{'form':form,'items':items,'order':entry,'editing':bool(pk),'variants_data':list(__import__('apps.landing.models',fromlist=['ProductVariant']).ProductVariant.objects.select_related('product').values('id','name','product__name','estimated_price','length_cm','width_cm','height_cm'))})

@staff_only
@require_POST
def send(request,pk):
    expire_quotes()
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind='quote')
        try:schedule_dispatch(send_quotation(entry,request.user))
        except ValidationError as error:messages.error(request,' '.join(error.messages))
        else:messages.success(request,'Cotización preparada para enviar. Consulta abajo el estado del correo y su vigencia.')
    return redirect('management:workflow_detail',pk=pk)

@staff_only
@require_POST
def confirm(request,pk):
    expire_quotes()
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk)
        form=ConfirmationForm(request.POST)
        if not form.is_valid():
            context=detail_context(entry);context['confirmation_form']=form
            return render(request,'management/workflow_detail.html',context,status=400)
        try:
            confirm_quotation(entry,form.cleaned_data['channel'],form.cleaned_data['note'],request.user,form.cleaned_data['estimated_delivery_date'])
        except ValidationError as error:messages.error(request,' '.join(error.messages))
        else:messages.success(request,'Pedido confirmado. Los abonos se registran por separado.')
    return redirect('management:workflow_detail',pk=pk)

@staff_only
@require_POST
def renew(request,pk):
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk)
        try:renew_quotation(entry,request.user)
        except ValidationError as error:messages.error(request,' '.join(error.messages))
        else:messages.success(request,'Nueva versión preparada. Revisa y vuelve a enviar.')
    return redirect('management:workflow_detail',pk=pk)

@never_cache
@customer_headers
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def customer_quote(request,token):
    # Mail scanners may follow GET links. Only an explicit CSRF-protected POST approves.
    expire_quotes()
    error='';entry=None
    try:
        with transaction.atomic():
            entry=entry_from_token(token,lock=request.method=='POST')
            if entry.kind=='order' and entry.approved_at:
                return render(request,'management/customer_quote.html',{'order':entry,'confirmed':True})
            if entry.kind!='quote' or entry.status!='sent' or not entry.quote_expires_at or entry.quote_expires_at<=timezone.now():
                raise ValidationError('La cotización venció o fue sustituida. Solicita una nueva versión a VillaTech.')
            if request.method=='POST':
                if request.POST.get('accept')!='yes':
                    return render(request,'management/customer_quote.html',{'order':entry,'accept_error':'Marca la aceptación para confirmar el pedido.'},status=400)
                confirm_quotation(entry,'email','Aceptación mediante el enlace de la cotización.')
                return redirect('management:customer_quote',token=token)
    except ValidationError as exc:error=' '.join(exc.messages)
    response=render(request,'management/customer_quote.html',{'order':entry if not error else None,'error':error})
    response['Referrer-Policy']='no-referrer';response['X-Robots-Tag']='noindex, nofollow'
    return response
