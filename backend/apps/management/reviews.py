"""Private invitations and explicitly published customer reviews."""
import uuid
from pathlib import Path
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse,Http404
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST,require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from .views import staff_only
from .models import Entry,QuoteItem,ProductReview,Payment,EntryActivity
from .workflow import complete_delivery
from apps.landing.models import Product

class EntryPhotosForm(forms.ModelForm):
    class Meta:
        model=Entry
        fields=['image','final_image']
        labels={'image':'Imagen de referencia','final_image':'Producto final entregado'}
class ItemPhotosForm(EntryPhotosForm):
    class Meta(EntryPhotosForm.Meta):model=QuoteItem

class ReviewSetupForm(forms.ModelForm):
    class Meta:
        model=ProductReview
        fields=['product','product_title','reference_image','final_image','is_active']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['product_title'].required=False
        self.fields['product'].label='Producto del inventario (opcional)'
        self.fields['product_title'].help_text='Este título lo defines tú; el cliente solo escribe su nombre, califica y deja su opinión.'
        self.fields['reference_image'].required=not bool(self.instance.reference_image)
        self.fields['final_image'].required=not bool(self.instance.final_image)
        self.fields['is_active'].help_text='Desmárcalo para revocar el acceso al formulario.'
    def clean(self):
        data=super().clean()
        if not data.get('product_title') and data.get('product'):data['product_title']=data['product'].name
        if not data.get('product_title'):self.add_error('product_title','Escribe el título del producto o selecciona uno del inventario.')
        return data

class CustomerReviewForm(forms.Form):
    full_name=forms.CharField(label='Nombre completo',max_length=255,min_length=3)
    rating=forms.TypedChoiceField(label='Califica tu producto',choices=[(i,f'{i} estrella'+('s' if i!=1 else '')) for i in range(1,6)],coerce=int,widget=forms.RadioSelect)
    comment=forms.CharField(label='Tu opinión (opcional)',required=False,max_length=2000,widget=forms.Textarea(attrs={'rows':4,'placeholder':'Cuéntanos cómo fue tu experiencia…','maxlength':2000}))
    consent=forms.BooleanField(label='Autorizo publicar mi nombre, calificación, opinión y las imágenes de este producto en la página de VillaTech.')

def published_reviews():
    return ProductReview.objects.filter(is_published=True,submitted_at__isnull=False,consent=True,rating__gte=1,rating__lte=5).exclude(reference_image='').exclude(final_image='')

def review_link(review):return settings.PUBLIC_SITE_URL.rstrip('/')+reverse('management:customer_review',args=[review.token])

def copy_image(source,target):
    if source and not target:
        try:
            with source.open('rb') as stream:target.save('opinion'+Path(source.name).suffix,ContentFile(stream.read()),save=True)
        except FileNotFoundError:
            __import__('logging').getLogger(__name__).warning('No se encontró la referencia original; completa la imagen en la invitación.')

@staff_only
@require_http_methods(['GET','POST'])
def photos(request,pk,item_pk=None):
    entry=get_object_or_404(Entry,pk=pk,kind__in=['order','sale'])
    subject=get_object_or_404(QuoteItem,pk=item_pk,order=entry) if item_pk else entry
    form=(ItemPhotosForm if item_pk else EntryPhotosForm)(request.POST or None,request.FILES or None,instance=subject)
    if request.method=='POST' and form.is_valid():
        saved=form.save(commit=False);saved.save(update_fields=['image','final_image']);messages.success(request,'Imágenes guardadas. Se mantienen privadas hasta publicar una opinión autorizada.')
        return redirect('management:workflow_detail',pk=pk)
    return render(request,'management/review_photos.html',{'form':form,'order':entry,'subject':subject})

@staff_only
@require_POST
def settle_delivered(request,pk):
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind__in=['order','sale'])
        if entry.kind=='sale':messages.info(request,'Este registro ya está cerrado. No se duplicó el pago.')
        elif entry.status!='delivered_due':messages.error(request,'Este botón solo cobra pedidos entregados con saldo pendiente.')
        else:
            due=entry.outstanding
            if due:
                Payment.objects.create(entry=entry,amount=due,created_by=request.user)
                entry.paid_amount+=due;entry.save(update_fields=['paid_amount','updated_at'])
                EntryActivity.objects.create(entry=entry,label='Pago final recibido',note=f'{due:.2f} COP. Registrado desde el botón de cobro.',actor=request.user)
            complete_delivery(entry,request.user)
            messages.success(request,'Pago registrado: pedido entregado y cerrado como venta.')
    return redirect('management:workflow_detail',pk=pk)

@staff_only
def review_list(request):
    from django.core.paginator import Paginator
    entries=ProductReview.objects.select_related('entry','product','item')
    state=request.GET.get('state','')
    if state=='pending':entries=entries.filter(submitted_at__isnull=True)
    elif state=='received':entries=entries.filter(submitted_at__isnull=False,is_published=False)
    elif state=='published':entries=entries.filter(is_published=True)
    return render(request,'management/reviews.html',{'page':Paginator(entries,25).get_page(request.GET.get('page')),'state':state})

@staff_only
@require_POST
def prepare_review(request,pk,item_pk=None):
    with transaction.atomic():
        entry=get_object_or_404(Entry.objects.select_for_update(),pk=pk,kind__in=['order','sale'])
        if not entry.can_review:
            messages.error(request,'Entrega el pedido antes de generar la opinión.');return redirect('management:workflow_detail',pk=pk)
        item=get_object_or_404(QuoteItem,pk=item_pk,order=entry) if item_pk else None
        subject=item or entry;product=item.product if item else entry.reference_product
        if not product and item and item.variant_id:product=item.variant.product
        review,created=ProductReview.objects.get_or_create(entry=entry,subject_key=f'item:{item.pk}' if item else 'entry',defaults={'item':item,'product':product,'product_title':item.name if item else entry.title,'quantity':subject.quantity})
        if created:
            copy_image(subject.image,review.reference_image);copy_image(subject.final_image,review.final_image)
    return redirect('management:review_edit',pk=review.pk)

@staff_only
@require_http_methods(['GET','POST'])
def review_edit(request,pk):
    review=get_object_or_404(ProductReview.objects.select_related('entry'),pk=pk)
    form=ReviewSetupForm(request.POST or None,request.FILES or None,instance=review)
    if request.method=='POST':
        with transaction.atomic():
            locked=ProductReview.objects.select_for_update().get(pk=pk)
            review=locked
            form=ReviewSetupForm(request.POST,request.FILES,instance=locked)
            if locked.submitted_at:messages.error(request,'La respuesta ya fue enviada; conserva el contenido que calificó el cliente.')
            elif form.is_valid():
                form.save();messages.success(request,'Invitación guardada. Ya puedes compartir el enlace con el cliente.')
                return redirect('management:review_edit',pk=pk)
    return render(request,'management/review_edit.html',{'review':review,'form':form,'products_data':list(Product.objects.values('id','name')),'share_url':review_link(review) if review.reference_image and review.final_image and review.is_active else ''})

@staff_only
@require_POST
def review_action(request,pk):
    with transaction.atomic():
        review=get_object_or_404(ProductReview.objects.select_for_update(),pk=pk)
        action=request.POST.get('action','')
        if action=='publish' and review.submitted_at and review.consent and review.final_image and review.reference_image:
            review.is_published=True;review.save(update_fields=['is_published']);messages.success(request,'Opinión publicada en la página.')
        elif action=='hide':review.is_published=False;review.save(update_fields=['is_published']);messages.success(request,'Opinión oculta.')
        elif action=='revoke':review.is_active=False;review.save(update_fields=['is_active']);messages.success(request,'Enlace revocado.')
        elif action=='renew' and not review.submitted_at:
            review.token=uuid.uuid4();review.is_active=True;review.save(update_fields=['token','is_active']);messages.success(request,'Enlace renovado; el anterior dejó de funcionar.')
        else:messages.error(request,'Esta acción no está disponible para la opinión.')
    return redirect('management:review_edit',pk=pk)

@ensure_csrf_cookie
@require_http_methods(['GET','POST'])
def customer_review(request,token):
    review=get_object_or_404(ProductReview.objects.select_related('entry'),token=token,is_active=True)
    if not review.entry.can_review:raise Http404
    form=CustomerReviewForm(request.POST or None,initial={'full_name':review.entry.customer})
    if not review.reference_image or not review.final_image:raise Http404
    if request.method=='POST' and not review.submitted_at and form.is_valid():
        with transaction.atomic():
            review=ProductReview.objects.select_for_update().get(pk=review.pk)
            if review.token!=token or not review.is_active:raise Http404
            if review.entry.can_review and not review.submitted_at:
                for field in ('full_name','rating','comment','consent'):setattr(review,field,form.cleaned_data[field])
                review.submitted_at=timezone.now();review.is_published=False
                review.save(update_fields=['full_name','rating','comment','consent','submitted_at','is_published'])
        return redirect('management:customer_review',token=token)
    response=render(request,'management/customer_review.html',{'review':review,'form':form},status=400 if request.method=='POST' and not review.submitted_at and form.errors else 200)
    response['Referrer-Policy']='same-origin';response['Cache-Control']='private, no-store'
    return response

@require_http_methods(['GET'])
def review_image(request,pk,kind):
    review=get_object_or_404(ProductReview,pk=pk)
    allowed=published_reviews().filter(pk=pk).exists() or (request.user.is_authenticated and request.user.is_active and request.user.is_staff)
    if not allowed:
        try:allowed=review.is_active and review.entry.can_review and uuid.UUID(request.GET.get('token',''))==review.token
        except (ValueError,TypeError,AttributeError):allowed=False
    if not allowed:raise Http404
    image=review.reference_image if kind=='reference' else review.final_image if kind=='final' else None
    if not image:raise Http404
    try:response=FileResponse(image.open('rb'))
    except OSError:raise Http404 from None
    response['X-Content-Type-Options']='nosniff';response['Cache-Control']='private, no-store'
    return response

@staff_only
def entry_photo(request,pk,kind,item_pk=None):
    entry=get_object_or_404(Entry,pk=pk)
    obj=get_object_or_404(QuoteItem,pk=item_pk,order=entry) if item_pk else entry
    image=obj.image if kind=='reference' else obj.final_image if kind=='final' else None
    if not image:raise Http404
    try:response=FileResponse(image.open('rb'))
    except OSError:raise Http404 from None
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
    return response
