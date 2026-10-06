from django.shortcuts import render

from .models import Product


# Create your views here.
def recuperar_productos(request):
    data = Product.objects.all().exists

    print(data)
    context = {"prueba": data}

    return render(request, "landing/views/prueba.html", context)
