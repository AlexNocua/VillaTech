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
from .models import Entry, EntryActivity, CustomerIssue, OperationalEmail
from .forms import WorkflowForm, QuoteFormSet, ApprovalForm, DeliveryForm
from .quotations import expire_quotes, send_quotation, confirm_quotation, entry_from_token, renew_quotation, recalculate, approval_url
from .workflow import schedule_dispatch

class ConfirmationForm(ApprovalForm):
    channel=forms.ChoiceField(label='Confirmación recibida por',choices=[('message','Mensaje o respuesta de correo'),('internal','Aprobación en gestión')])
    note=forms.CharField(label='Referencia de la confirmación',max_length=255,required=True,
        help_text='Ejemplo: WhatsApp del cliente o respuesta de correo del 09 de octubre.')

def detail_context(entry):
    from pathlib import Path
    legacy_name=entry.contact.file.name if entry.contact_id and entry.contact.file else ''
    ext=Path(legacy_name).suffix.lower()
    legacy_kind='image' if ext in ('.jpg','.jpeg','.png','.webp') else 'video' if ext in ('.mp4','.webm','.mov') else 'document'
    return {'legacy_reference_kind':legacy_kind, 'legacy_reference_name':Path(legacy_name).name, ** {'order':entry,'delivery_form':DeliveryForm(initial={'estimated_delivery_date':entry.estimated_delivery_date,'status':entry.status}),'confirmation_form':ConfirmationForm(initial={'estimated_delivery_date':entry.estimated_delivery_date}),
        'share_url':approval_url(entry) if entry.kind=='quote' and entry.status=='sent' else ''}}

@staff_only
def board(request):
    expire_quotes()
    entries=Entry.objects.filter(kind__in=['quote','order','sale']).select_related('contact').prefetch_related('items','contact__attachments')
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
    entry=get_object_or_404(Entry.objects.prefetch_related('items','payments','activities','emails','customer_issues','contact__attachments'),pk=pk,kind__in=['quote','order','sale'])
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
    from django.urls import reverse
    support_url=reverse('management:customer_issue',args=[token])
    error='';entry=None
    try:
        with transaction.atomic():
            entry=entry_from_token(token,lock=request.method=='POST')
            if entry.kind in ('order','sale') and entry.approved_at:
                return render(request,'management/customer_quote.html',{'order':entry,'confirmed':True})
            if entry.kind=='quote' and entry.quote_expires_at and entry.quote_expires_at<=timezone.now():
                raise ValidationError('Se cumplieron las 48 horas de vigencia. Solicita el reenvío con un nuevo enlace.')
            if entry.kind=='quote' and entry.status=='sent' and not entry.quote_expires_at:
                raise ValidationError('El correo aún está pendiente de envío. VillaTech puede reintentar el envío o generar un enlace nuevo.')
            if entry.kind!='quote' or entry.status!='sent':
                raise ValidationError('Esta versión ya no está disponible. Solicita un nuevo enlace a VillaTech.')
            if request.method=='POST':
                if request.POST.get('accept')!='yes':
                    return render(request,'management/customer_quote.html',{'order':entry,'support_url':support_url,'accept_error':'Marca la aceptación para confirmar el pedido.'},status=400)
                confirm_quotation(entry,'email','Aceptación mediante el enlace de la cotización.')
                return redirect('management:customer_quote',token=token)
    except ValidationError as exc:error=' '.join(exc.messages)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Error al confirmar cotización del cliente')
        error='No pudimos completar la confirmación. Puedes reportar lo ocurrido y solicitar un nuevo enlace.'
    response=render(request,'management/customer_quote.html',{'order':entry if not error else None,'error':error,'support_url':__import__('django.urls',fromlist=['reverse']).reverse('management:customer_issue',args=[token])})
    response['Referrer-Policy']='same-origin';response['X-Robots-Tag']='noindex, nofollow'
    return response


@staff_only
@require_POST
def resend(request, pk):
    with transaction.atomic():
        entry = get_object_or_404(Entry.objects.select_for_update(), pk=pk, kind='quote')
        try:
            if request.POST.get('version') and request.POST['version'] != str(entry.approval_nonce):
                raise ValidationError('Ya se generó otra URL. Abre la ficha para revisar el envío más reciente.')
            renew_quotation(entry, request.user)
            schedule_dispatch(send_quotation(entry, request.user))
        except ValidationError as error:
            transaction.set_rollback(True)
            messages.error(request, ' '.join(error.messages))
        else:
            messages.success(request, 'Nuevo enlace generado. Sus 48 horas empiezan cuando se acepta el correo. El enlace anterior queda reemplazado.')
    return redirect('management:workflow_detail', pk=pk)


class CustomerIssueForm(forms.Form):
    customer_email = forms.EmailField(label='Tu correo para responderte', required=False)
    comment = forms.CharField(label='Cuéntanos qué ocurrió', min_length=5, max_length=2000,
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe el problema al confirmar tu pedido…'}))


@never_cache
@customer_headers
@ensure_csrf_cookie
@require_http_methods(['GET','POST'])
def customer_issue(request, token):
    from hashlib import sha256
    from django.core.cache import cache
    from django.conf import settings
    from django.core import signing
    from django.template.loader import render_to_string
    from django.urls import reverse
    from .quotations import SALT
    form = CustomerIssueForm(request.POST or None)
    entry = None
    # An older, correctly signed link may report a problem, but never approve.
    try:
        data = signing.loads(token, salt=SALT)
        entry = Entry.objects.filter(pk=data['id']).first()
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        pass
    if request.method == 'POST' and form.is_valid():
        key = 'quote-issue:' + sha256((request.META.get('REMOTE_ADDR','unknown') + ':' + token).encode()).hexdigest()
        if not cache.add(key, 1, 3600):
            try:
                attempts = cache.incr(key)
            except ValueError:
                cache.set(key, 1, 3600); attempts = 1
        else:
            attempts = 1
        if attempts > 5:
            form.add_error(None, 'Ya recibimos varios reportes. Espera una hora o responde al correo de tu cotización.')
        else:
            try:
                with transaction.atomic():
                    if entry:
                        entry = Entry.objects.select_for_update().filter(pk=entry.pk).first()
                    issue = CustomerIssue.objects.create(entry=entry, **form.cleaned_data)
                    context = {'issue':issue, 'heading':'Problema al confirmar una cotización',
                        'management_url':settings.PUBLIC_SITE_URL.rstrip('/') + (reverse('management:workflow_detail', args=[entry.pk]) if entry else reverse('management:workflow'))}
                    message = OperationalEmail.objects.create(entry=entry, event_key=f'issue:{issue.pk}',
                        recipient=settings.CONTACT_NOTIFICATION_EMAIL,
                        subject=f'VillaTech · Reporte de confirmación #{issue.pk}',
                        text=render_to_string('management/emails/issue.txt',context),
                        html=render_to_string('management/emails/issue.html',context))
                    if entry:
                        EntryActivity.objects.create(entry=entry,label='El cliente reportó un problema',note=f'Reporte #{issue.pk}. Consulta el comentario en la ficha.')
                    schedule_dispatch(message)
            except Exception:
                import logging
                logging.getLogger(__name__).exception('No se pudo registrar el comentario del cliente')
                form.add_error(None, 'No pudimos guardar tu comentario. Tu información sigue aquí; intenta nuevamente.')
            else:
                return redirect(reverse('management:customer_issue',args=[token])+'?received=1')
    return render(request,'management/customer_issue.html',{'form':form,'received':request.GET.get('received')=='1',
        'quote_url':reverse('management:customer_quote',args=[token])})


@staff_only
@require_http_methods(['GET','POST'])
def delete_entry(request, pk):
    from .cleanup import delete_commercial_entry
    entry = get_object_or_404(Entry, pk=pk, kind__in=['quote','order','sale'])
    if request.method == 'POST':
        if request.POST.get('confirm_delete') != str(pk):
            return render(request,'management/delete_entry.html',{'order':entry,'error':'Marca la confirmación para eliminar este registro.'},status=400)
        with transaction.atomic():
            entry = get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind__in=['quote','order','sale'])
            delete_commercial_entry(entry)
        messages.success(request,'Registro eliminado. Los totales se recalcularon sin este registro.')
        return redirect('management:workflow')
    return render(request,'management/delete_entry.html',{'order':entry})


@staff_only
@require_POST
def bulk_delete(request):
    from .cleanup import delete_commercial_entry
    raw_ids = request.POST.getlist('entries')
    if not raw_ids or len(raw_ids) > 100 or any(not value.isdecimal() or len(value)>12 for value in raw_ids):
        messages.error(request, 'Selecciona entre 1 y 100 registros para depurar.')
        return redirect('management:workflow')
    ids = sorted(set(int(value) for value in raw_ids))
    if request.POST.get('confirm_delete') != 'yes':
        records = list(Entry.objects.filter(pk__in=ids,kind__in=['quote','order','sale']))
        return render(request,'management/bulk_delete.html',{'records':records})
    with transaction.atomic():
        records = list(Entry.objects.select_for_update().filter(pk__in=ids,kind__in=['quote','order','sale']).order_by('pk'))
        count = len(records)
        for entry in records:
            delete_commercial_entry(entry)
    messages.success(request, f'{count} registros eliminados. Los totales fueron recalculados.')
    return redirect('management:workflow')
