from django.contrib import admin
from django.urls import include, path


from apps.landing.media import catalog_image

from .health import health

urlpatterns = [
    path("healthz/", health),
    path("media/catalog/<str:name>", catalog_image),
    # Rutas APP inventory con desglose de rutas api y redner
    path("gestion/", include("apps.management.urls")),
    path("admin/", admin.site.urls),
    # rutas de APIs
    path("api/", include("apps.inventary.api.urls")),
    # rutas de Aplicaciones
    path("", include("apps.landing.urls")),

]
