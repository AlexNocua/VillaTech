from django.db import models


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
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

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
    telephone=models.IntegerField(blank=False)
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

class ContactAttachment(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=private_path)


