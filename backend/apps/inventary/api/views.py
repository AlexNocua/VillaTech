from rest_framework import viewsets

from apps.inventary.models import Product
from apps.inventary.api.serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-id")
    serializer_class = ProductSerializer
