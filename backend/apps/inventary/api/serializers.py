from rest_framework import serializers

from apps.inventary.models import Product


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "description",
            "price",
            "stock",
            "image_url",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
