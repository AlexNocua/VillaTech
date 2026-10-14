from django.contrib import admin
from django.urls import include, path
from .views import recuperar_productos,contact_form_action,product_detail
app_name  = "landing"

urlpatterns = [
    path('productos/<int:pk>/',product_detail,name='product_detail'),
    # Rutas APP inventory con desglose de rutas api y redner
    path("", recuperar_productos, name="recuperar_productos"),
    path("submit", contact_form_action, name="contact_form_action")
]
