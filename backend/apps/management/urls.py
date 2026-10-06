from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views
app_name='management'
urlpatterns=[
 path('solicitudes/archivo/<int:pk>/',views.legacy_contact_file,name='legacy_contact_file'),
 path('pedidos/',views.entry_list,name='orders'),
 path('cotizaciones/',views.entry_list,{'section':'quotes'},name='quotes'),
 path('solicitudes/adjunto/<int:pk>/',views.contact_attachment,name='contact_attachment'),
 path('solicitudes/<int:pk>/reintentar-correos/',views.retry_notifications,name='retry_notifications'),
 path('desarrollo/',views.development,name='development'),
 path('desarrollo/<int:pk>/',views.development,name='development_edit'),
 path('desarrollo/captura/<int:pk>/',views.screenshot,name='screenshot'),
 path('calculadora/proceso/',views.estimate,name='estimate'),
 path('registro/<int:pk>/convertir/<str:target>/',views.transition,name='transition'),
 path('categorias/',views.categories,name='categories'),
 path('categorias/<int:pk>/',views.categories,name='category_edit'),
 path('productos/',views.products,name='products'),
 path('productos/<int:pk>/',views.products,name='product_edit'),
 path('impresoras/',views.printers,name='printers'),
 path('impresoras/<int:pk>/',views.printers,name='printer_edit'),
 path('cotizacion/<int:pk>/',views.quote_detail,name='quote_detail'),
 path('cotizacion/<int:pk>/pdf/',views.quote_pdf,name='quote_pdf'),
 path('',views.dashboard,name='dashboard'),
 path('ingresar/',LoginView.as_view(template_name='management/login.html'),name='login'),
 path('salir/',LogoutView.as_view(),name='logout'),
 path('registro/<str:kind>/',views.entry_form,name='create'),
 path('registro/<str:kind>/<int:pk>/',views.entry_form,name='edit'),
 path('producto/',views.catalog_form,name='product'),
 path('variante/',views.catalog_form,{'variant':True},name='variant'),
 path('calculadora/',views.calculator,name='calculator'),
 path('imagen/<int:pk>/',views.image,name='image'),
]
