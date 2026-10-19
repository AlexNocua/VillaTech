import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator,MaxValueValidator
from apps.landing.validators import private_path, validate_image, validate_print_model

class Entry(models.Model):
    KIND = [('quote','Cotización'),('sale','Venta'),('order','Pedido'),('expense','Gasto')]
    CATEGORY = [('filament','Compra de filamento'),('monthly','Pago mensual'),('maintenance','Mantenimiento'),('energy','Energía'),('software','Software y licencias'),('supplies','Insumos'),('services','Servicios'),('other','Otro')]
    STATUS = [('draft','Borrador'),('quoted','Preparada'),('sent','Enviada'),('expired','Vencida'),('sold','Vendido'),('pending','Pendiente'),('printing','En impresión'),('ready','Listo'),('delivered','Entregado'),('delivered_due','Entregado sin pagar'),('cancelled','Cancelado')]
    kind = models.CharField('Tipo', max_length=10, choices=KIND)
    title = models.CharField('Descripción', max_length=150)
    description = models.TextField('Descripción del producto / proyecto', blank=True)
    product_category = models.ForeignKey('landing.CategoryProduct',verbose_name='Categoría de producto',on_delete=models.PROTECT,null=True,blank=True)
    reference_product = models.ForeignKey('landing.Product',verbose_name='Producto de referencia (opcional)',on_delete=models.SET_NULL,null=True,blank=True)
    print_hours = models.DecimalField('Horas de impresión',max_digits=10,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    sold_at = models.DateTimeField('Fecha de venta',null=True,blank=True,editable=False)
    customer = models.CharField('Cliente', max_length=150, blank=True)
    paid_amount = models.DecimalField('Total abonado COP', max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    delivery_settled_amount = models.DecimalField('Saldo liquidado al entregar COP', max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    amount = models.DecimalField('Valor total COP', max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.CharField('Categoría de gasto', max_length=15, choices=CATEGORY, default='other')
    status = models.CharField('Estado del pedido', max_length=15, choices=STATUS, default='pending')
    filament_g = models.DecimalField('Filamento consumido (g)', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    acquired_filament_g = models.DecimalField('Filamento adquirido (g)', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField('Imagen de referencia', upload_to=private_path, blank=True, validators=[validate_image])
    final_image = models.ImageField('Producto final entregado',upload_to=private_path,blank=True,validators=[validate_image])
    quotation_pdf = models.FileField(upload_to=private_path, blank=True, editable=False)
    logo_theme = models.CharField('Logo del PDF', max_length=5, choices=[('light','Blanco'),('dark','Negro')], default='light')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    source = models.CharField('Origen', max_length=10, choices=[('manual','Gestión'),('web','Página web')], default='manual')
    contact = models.OneToOneField('landing.Contact', on_delete=models.PROTECT, null=True, blank=True, related_name='entry')
    customer_email = models.EmailField('Correo del cliente', blank=True)
    customer_phone = models.CharField('Teléfono del cliente', max_length=25, blank=True)
    estimated_delivery_date = models.DateField('Entrega estimada', null=True, blank=True)
    quantity = models.PositiveIntegerField('Unidades', default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('Precio unitario COP', max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    unit_filament_g = models.DecimalField('Filamento por unidad g', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    unit_print_hours = models.DecimalField('Horas por unidad', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    quote_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    quote_expires_at = models.DateTimeField(null=True, blank=True, editable=False)
    approval_nonce = models.UUIDField(default=uuid.uuid4, editable=False)
    approval_channel = models.CharField('Medio de confirmación', max_length=10, choices=[('email','Enlace del correo'),('message','Mensaje'),('internal','Gestión')], blank=True)
    approval_note = models.CharField('Referencia de confirmación', max_length=255, blank=True)
    approved_at = models.DateTimeField('Confirmado el', null=True, blank=True, editable=False)
    class Meta:
        ordering = ['-created_at']
    def save(self,*args,**kwargs):
        if self.kind == 'sale':
            from django.utils import timezone
            self.status='sold'
            if not self.sold_at:self.sold_at=timezone.now()
        super().save(*args,**kwargs)
    @property
    def delivered_unpaid(self):
        return self.status=='delivered_due' and self.outstanding>0
    @property
    def can_review(self):
        return self.kind=='sale' or self.status in ('delivered','delivered_due')
    @property
    def payment_status(self):
        if self.kind not in ('order','sale') or self.status=='cancelled':return 'not_applicable'
        if self.amount<=0:return 'no_charge'
        if self.paid_amount>=self.amount:return 'paid'
        return 'partial' if self.paid_amount else 'unpaid'
    @property
    def payment_label(self):
        return {'paid':'Pagado / liquidado','partial':'Abono parcial','unpaid':'Sin pago','no_charge':'Sin cargo','not_applicable':'No aplica'}[self.payment_status]
    @property
    def outstanding(self):
        return max(self.amount - self.paid_amount, 0) if self.kind in ('order','sale') and self.status != 'cancelled' else 0
    @property
    def delivery_alert(self):
        from django.utils import timezone
        from datetime import timedelta
        if self.kind != 'order' or self.status in ('delivered','delivered_due','cancelled','sold'):
            return ''
        if not self.estimated_delivery_date:
            return 'Sin fecha'
        today = timezone.localdate()
        if self.estimated_delivery_date < today:
            return 'Vencido'
        if self.estimated_delivery_date == today:
            return 'Entrega hoy'
        if self.estimated_delivery_date <= today + timedelta(days=3):
            return 'Próximo a vencer'
        return 'Programado'
    @property
    def total_units(self):
        return sum(i.quantity for i in self.items.all()) if self.pk and self.items.exists() else self.quantity
    def __str__(self): return self.title


class PrinterProfile(models.Model):
    name = models.CharField('Impresora', max_length=100, unique=True)
    rated_watts = models.PositiveIntegerField('Potencia nominal (W)', null=True, blank=True)
    average_watts = models.DecimalField('Potencia media medida (W)', max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    purchase_price = models.DecimalField('Costo de adquisición COP',max_digits=14,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    useful_hours = models.PositiveIntegerField('Vida útil estimada (h)',default=10000,validators=[MinValueValidator(1)])
    maintenance_hour = models.DecimalField('Reserva mantenimiento COP/h',max_digits=10,decimal_places=2,default=200,validators=[MinValueValidator(0)])
    def __str__(self):return self.name

class QuoteItem(models.Model):
    order = models.ForeignKey(Entry,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey('landing.Product',verbose_name='Producto existente',on_delete=models.SET_NULL,null=True,blank=True,related_name='quotation_lines')
    variant = models.ForeignKey('landing.ProductVariant',on_delete=models.SET_NULL,null=True,blank=True)
    name = models.CharField('Producto / descripción',max_length=160)
    length_cm = models.DecimalField('Largo cm',max_digits=7,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    width_cm = models.DecimalField('Ancho cm',max_digits=7,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    height_cm = models.DecimalField('Alto cm',max_digits=7,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField('Cantidad',default=1,validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('Precio unitario COP',max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    image = models.ImageField('Imagen del producto',upload_to=private_path,blank=True,validators=[validate_image])
    final_image = models.ImageField('Producto final entregado',upload_to=private_path,blank=True,validators=[validate_image])
    description = models.TextField('Descripción y acabado', blank=True)
    unit_filament_g = models.DecimalField('Filamento por unidad g',max_digits=10,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    unit_print_hours = models.DecimalField('Horas por unidad',max_digits=10,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    comparison_image = models.ImageField('Imagen de comparación / escala',upload_to=private_path,blank=True,validators=[validate_image])
    @property
    def filament_total(self):return self.quantity*self.unit_filament_g
    @property
    def hours_total(self):return self.quantity*self.unit_print_hours
    @property
    def total(self):return self.quantity*self.unit_price


class DevelopmentProject(models.Model):
    TYPES=[('design','Diseño digital / UX'),('web','Desarrollo web'),('mobile','Aplicación móvil'),('software','Software a medida'),('automation','Automatización')]
    STATES=[('planned','Planificado'),('active','En desarrollo'),('paused','En pausa'),('delivered','Finalizado')]
    name=models.CharField('Nombre del proyecto',max_length=160)
    project_type=models.CharField('Tipo de trabajo',max_length=15,choices=TYPES,default='software')
    description=models.TextField('Qué hace el aplicativo / alcance')
    customer=models.CharField('Cliente',max_length=150,blank=True)
    status=models.CharField('Estado',max_length=15,choices=STATES,default='active')
    started_on=models.DateField('Fecha de inicio',null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:ordering=['-updated_at']
    def __str__(self):return self.name

class ProjectScreenshot(models.Model):
    project=models.ForeignKey(DevelopmentProject,on_delete=models.CASCADE,related_name='screenshots')
    image=models.ImageField('Captura del aplicativo',upload_to=private_path,validators=[validate_image])
    created_at=models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    entry=models.ForeignKey(Entry,on_delete=models.CASCADE,related_name='payments')
    amount=models.DecimalField('Abono COP',max_digits=14,decimal_places=2,validators=[MinValueValidator(0.01)])
    created_at=models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        ordering=['-created_at','-pk']

class StockMovement(models.Model):
    product=models.ForeignKey('landing.Product',on_delete=models.PROTECT,related_name='stock_movements')
    quantity=models.BigIntegerField('Cambio de unidades')
    reason=models.CharField('Motivo',max_length=150)
    created_at=models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        ordering=['-created_at','-pk']


class OperationalEmail(models.Model):
    """Immutable event snapshot; failed delivery can be retried without losing the order."""
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, null=True, blank=True, related_name='emails')
    event_key = models.CharField(max_length=160, unique=True)
    recipient = models.EmailField(blank=True)
    subject = models.CharField(max_length=255)
    text = models.TextField()
    html = models.TextField()
    status = models.CharField(max_length=10, choices=[('pending','Pendiente'),('sent','Enviado'),('failed','Falló'),('skipped','Descartado')], default='pending')
    attachment = models.FileField(upload_to=private_path, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at','-pk']


class EntryActivity(models.Model):
    entry = models.ForeignKey(Entry,on_delete=models.CASCADE,related_name='activities')
    label = models.CharField(max_length=120)
    note = models.CharField(max_length=255,blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at','-pk']


class CustomerIssue(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_issues')
    customer_email = models.EmailField('Correo para responder', blank=True)
    comment = models.TextField('¿Qué ocurrió?', max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-pk']

class PrintingModel(models.Model):
    title=models.CharField('Nombre del modelo',max_length=150)
    description=models.TextField('Descripción',blank=True)
    file=models.FileField('Archivo STL o 3MF',upload_to=private_path,validators=[validate_print_model])
    original_name=models.CharField(max_length=255,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at']


class ProductReview(models.Model):
    entry=models.ForeignKey(Entry,on_delete=models.CASCADE,related_name='reviews',null=True,blank=True)
    development=models.ForeignKey(DevelopmentProject,on_delete=models.CASCADE,related_name='reviews',null=True,blank=True)
    review_type=models.CharField('Tipo de experiencia',max_length=10,choices=[('product','Impresión 3D / producto'),('software','Software / desarrollo')],default='product')
    public_summary=models.TextField('Descripción pública (opcional)',blank=True,max_length=1000)
    item=models.ForeignKey(QuoteItem,on_delete=models.SET_NULL,null=True,blank=True,related_name='reviews')
    subject_key=models.CharField(max_length=32)
    token=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    product=models.ForeignKey('landing.Product',on_delete=models.SET_NULL,null=True,blank=True)
    product_title=models.CharField('Título del producto',max_length=160)
    quantity=models.PositiveIntegerField(default=1)
    reference_image=models.ImageField('Imagen de referencia',upload_to=private_path,blank=True,validators=[validate_image])
    final_image=models.ImageField('Imagen del producto final',upload_to=private_path,blank=True,validators=[validate_image])
    full_name=models.CharField('Nombre completo',max_length=255,blank=True)
    rating=models.PositiveSmallIntegerField('Calificación',null=True,blank=True,validators=[MinValueValidator(1),MaxValueValidator(5)])
    comment=models.TextField('Opinión (opcional)',blank=True,max_length=2000)
    consent=models.BooleanField(default=False)
    is_active=models.BooleanField('Enlace habilitado',default=True)
    is_published=models.BooleanField('Publicar en la página',default=False)
    submitted_at=models.DateTimeField(null=True,blank=True,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-submitted_at','-created_at']
        constraints=[models.UniqueConstraint(fields=['entry','subject_key'],name='unique_entry_review_subject'),models.UniqueConstraint(fields=['development','subject_key'],name='unique_project_review_subject'),models.CheckConstraint(condition=(models.Q(entry__isnull=False,development__isnull=True)|models.Q(entry__isnull=True,development__isnull=False)),name='review_has_one_origin')]
    @property
    def stars(self):return range(self.rating or 0)
    @property
    def empty_stars(self):return range(5-(self.rating or 0))

    @property
    def can_review(self):return self.entry.can_review if self.entry_id else self.development.status=='delivered' if self.development_id else False
    @property
    def customer_name(self):return self.entry.customer if self.entry_id else self.development.customer if self.development_id else ''
    @property
    def origin_label(self):return f'Pedido VT-{self.entry_id}' if self.entry_id else f'Proyecto SW-{self.development_id}'
    @property
    def subject_word(self):return 'proyecto' if self.review_type=='software' else 'producto'
    @property
    def verified_label(self):return 'Desarrollo verificado' if self.review_type=='software' else 'Compra verificada'
    @property
    def final_label(self):return 'Software entregado' if self.review_type=='software' else 'Producto final'
    @property
    def reference_label(self):return 'Referencia / propuesta' if self.review_type=='software' else 'La idea'
