from django.contrib import admin
from .models import Client, Product, Purchase


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone")
    search_fields = ("name", "email", "phone")
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "_type", "price")
    search_fields = ("name", "_type")
    list_filter = ("_type",)
    ordering = ("name",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "order_purchase", "client", "date", "total")
    search_fields = ("order_purchase", "client__name")
    list_filter = ("date",)
    ordering = ("-date",)

    # Permite seleccionar productos fácilmente
    filter_horizontal = ("products",)