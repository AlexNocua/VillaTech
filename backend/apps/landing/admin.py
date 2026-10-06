from django.contrib import admin
from .models import Product, CategoryProduct, Tags, Contact

# Register your models here.


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "mtm_category__category_name",
        "image_url",
        "is_active",
    )
    list_filter = ("name",)
    list_field = ("name",)


@admin.register(CategoryProduct)
class CategoryProductAdmin(admin.ModelAdmin):
    list_display = ("category_name",)
    list_filter = ("category_name", "is_active")
    list_field = ("category_name",)


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ("tag_name",)
    list_filter = ("tag_name",)
    list_field = ("tag_name",)
    
    
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("client_name",)
    list_filter = ("client_name",)
    list_field = ("client_name",)

from .models import ProductVariant
class VariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
ProductAdmin.inlines = [VariantInline]
admin.site.register(ProductVariant)
