from django.db import models

# un cliente puede ralizar muchas compras
class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name

# un producto puiede estar en muchas compras
class Product(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField()
    _type = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    img = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

# una compra puede tener muchos productos 
class Purchase(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="purchases"
    )

    products = models.ManyToManyField(
        Product,
        related_name="purchases"
    )

    order_purchase = models.IntegerField(unique=True)
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Compra #{self.order_purchase}"