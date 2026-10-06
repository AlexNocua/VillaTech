from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from apps.landing.validators import private_path, validate_image

class Entry(models.Model):
    KIND = [('quote','Cotización'),('sale','Venta'),('order','Pedido'),('expense','Gasto')]
    CATEGORY = [('filament','Compra de filamento'),('monthly','Pago mensual'),('maintenance','Mantenimiento'),('energy','Energía'),('software','Software y licencias'),('supplies','Insumos'),('services','Servicios'),('other','Otro')]
    STATUS = [('draft','Borrador'),('quoted','Cotizado'),('sold','Vendido'),('pending','Pendiente'),('printing','En impresión'),('ready','Listo'),('delivered','Entregado'),('cancelled','Cancelado')]
    kind = models.CharField('Tipo', max_length=10, choices=KIND)
    title = models.CharField('Descripción', max_length=150)
    description = models.TextField('Descripción del producto / proyecto', blank=True)
    product_category = models.ForeignKey('landing.CategoryProduct',verbose_name='Categoría de producto',on_delete=models.PROTECT,null=True,blank=True)
    reference_product = models.ForeignKey('landing.Product',verbose_name='Producto de referencia (opcional)',on_delete=models.SET_NULL,null=True,blank=True)
    print_hours = models.DecimalField('Horas de impresión',max_digits=10,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    sold_at = models.DateTimeField('Fecha de venta',null=True,blank=True,editable=False)
    customer = models.CharField('Cliente', max_length=150, blank=True)
    amount = models.DecimalField('Valor total COP', max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.CharField('Categoría de gasto', max_length=15, choices=CATEGORY, default='other')
    status = models.CharField('Estado del pedido', max_length=15, choices=STATUS, default='pending')
    filament_g = models.DecimalField('Filamento consumido (g)', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    acquired_filament_g = models.DecimalField('Filamento adquirido (g)', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField('Imagen de referencia', upload_to=private_path, blank=True, validators=[validate_image])
    quotation_pdf = models.FileField(upload_to=private_path, blank=True, editable=False)
    logo_theme = models.CharField('Logo del PDF', max_length=5, choices=[('light','Blanco'),('dark','Negro')], default='light')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    source = models.CharField('Origen', max_length=10, choices=[('manual','Gestión'),('web','Página web')], default='manual')
    contact = models.OneToOneField('landing.Contact', on_delete=models.PROTECT, null=True, blank=True, related_name='entry')
    customer_email = models.EmailField('Correo del cliente', blank=True)
    customer_phone = models.CharField('Teléfono del cliente', max_length=25, blank=True)
    class Meta:
        ordering = ['-created_at']
    def save(self,*args,**kwargs):
        if self.kind == 'sale':
            from django.utils import timezone
            self.status='sold'
            if not self.sold_at:self.sold_at=timezone.now()
        super().save(*args,**kwargs)
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
    variant = models.ForeignKey('landing.ProductVariant',on_delete=models.SET_NULL,null=True,blank=True)
    name = models.CharField('Producto / descripción',max_length=160)
    length_cm = models.DecimalField('Largo cm',max_digits=7,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    width_cm = models.DecimalField('Ancho cm',max_digits=7,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    height_cm = models.DecimalField('Alto cm',max_digits=7,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField('Cantidad',default=1,validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('Precio unitario COP',max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    image = models.ImageField('Imagen del producto',upload_to=private_path,blank=True,validators=[validate_image])
    comparison_image = models.ImageField('Imagen de comparación / escala',upload_to=private_path,blank=True,validators=[validate_image])
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
