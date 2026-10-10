from django.db import models
from .validators import image_path, validate_image, private_path, validate_print_model


class CategoryProduct(models.Model):
    # CATEGORIAS = [
    #     ("L", "Llaveros"),
    #     ("T", "Técnicos"),
    #     ("F", "Figura"),
    # ]
    # categories = models.CharField(
    #     max_length=3, choices=CATEGORIAS, blank=True, default=list
    # )
    category_name = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.category_name


class Tags(models.Model):
    tag_name = models.CharField(max_length=20)

    def __str__(self):
        return self.tag_name


# Create your models here.
class Product(models.Model):
    is_public = models.BooleanField("Mostrar en la página web", default=False)
    fk_tags = models.ManyToManyField(Tags, related_name="productos")
    mtm_category = models.ForeignKey(
        CategoryProduct, on_delete=models.PROTECT, related_name="productos"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveBigIntegerField(default=0)
    image = models.ImageField('Imagen del producto', upload_to=image_path, validators=[validate_image], blank=True)
    print_model = models.FileField('Modelo de impresión', upload_to=private_path, blank=True, validators=[validate_print_model])
    print_model_original_name = models.CharField(max_length=255, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def display_image_url(self):
        return self.image.url if self.image else self.image_url

    @property
    def category_slug(self):
        value = slugify(self.mtm_category.category_name)
        return 'figuras' if value in ('figura', 'figuras') else value

    @property
    def tags(self):
        return [tag.tag_name for tag in self.fk_tags.all()]

    @property
    def price_display(self):
        return f'$ {self.price:,.0f} COP'


class Contact (models.Model):
    client_name=models.CharField(max_length=255)
    telephone=models.CharField('Teléfono',max_length=25,blank=False)
    email=models.EmailField(blank=True)
    service=models.CharField(max_length=50)
    message=models.CharField(max_length=500)
    file=models.FileField(upload_to="Files/%Y/" ,verbose_name="Archivo")
    date_create=models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creacion")

from django.core.validators import MinValueValidator
from django.utils.text import slugify
from .validators import image_path, private_path, validate_image

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField('Presentación', max_length=80)
    length_cm = models.DecimalField('Largo (cm)', max_digits=7, decimal_places=2, validators=[MinValueValidator(0.01)])
    width_cm = models.DecimalField('Ancho (cm)', max_digits=7, decimal_places=2, validators=[MinValueValidator(0.01)])
    height_cm = models.DecimalField('Alto (cm)', max_digits=7, decimal_places=2, validators=[MinValueValidator(0.01)])
    estimated_price = models.DecimalField('Precio estimado COP', max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField('Imagen', upload_to=image_path, validators=[validate_image], blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['estimated_price', 'pk']
    def __str__(self):
        return f'{self.product} · {self.name}'

class ContactEmail(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='notifications')
    audience = models.CharField(max_length=10, choices=[('customer','Cliente'),('admin','VillaTech')])
    recipient = models.EmailField(blank=True)
    subject = models.CharField(max_length=255)
    text = models.TextField()
    html = models.TextField()
    reply_to = models.EmailField(blank=True)
    status = models.CharField(max_length=10, default='pending', choices=[('pending','Pendiente'),('sent','Aceptado por proveedor'),('failed','Falló')])
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=160, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['contact','audience'], name='unique_contact_email_audience')]

class ContactAttachment(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=private_path)
    original_name = models.CharField(max_length=255, blank=True)
    @property
    def display_name(self):
        from pathlib import Path
        return self.original_name or Path(self.file.name).name
    @property
    def media_kind(self):
        from pathlib import Path
        ext = Path(self.file.name).suffix.lower()
        if ext in ('.png','.jpg','.jpeg','.webp'): return 'image'
        if ext in ('.mp4','.webm','.mov'): return 'video'
        return 'document'



