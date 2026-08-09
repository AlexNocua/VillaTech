from django.contrib import admin

# importacion de los modelosd e mi aplicacion

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "stock",
        "is_active",
        "create_at",
    )

    list_filter = (
        "is_active",
        "create_at",
    )

    search_field = ("name", "description")


# Register your models here.
