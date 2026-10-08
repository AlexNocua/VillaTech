import io
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from .models import Product, CategoryProduct, ProductVariant

def upload():
    stream = io.BytesIO(); Image.new('RGB', (8,8), 'green').save(stream, 'PNG')
    return SimpleUploadedFile('foto.png', stream.getvalue(), content_type='image/png')

class MediaTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp.name)
        override.enable(); self.addCleanup(override.disable)
        self.user = get_user_model().objects.create_user('media_staff', is_staff=True)
        self.client.force_login(self.user)
        self.category = CategoryProduct.objects.create(category_name='Figuras')
        self.product = Product.objects.create(name='Figura', price=10000, mtm_category=self.category, is_public=True)
    def test_edit_product_saves_uploaded_image_and_serves_publicly(self):
        response = self.client.post(f'/gestion/productos/{self.product.pk}/', {'name':'Figura','price':'10000','stock':'0','mtm_category':self.category.pk,'is_active':'on','is_public':'on','image':upload()})
        self.assertEqual(response.status_code,302)
        self.product.refresh_from_db()
        self.assertTrue(Path(self.product.image.path).is_file())
        self.client.logout()
        response = self.client.get(self.product.display_image_url)
        self.assertEqual(response.status_code,200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
        self.assertContains(self.client.get('/'),self.product.display_image_url)
        self.product.is_public=False; self.product.save()
        self.assertEqual(self.client.get(self.product.image.url).status_code,404)
    def test_variant_storage_survives_new_request_and_missing_file_is_404(self):
        variant = ProductVariant.objects.create(product=self.product,name='Pequeña',length_cm=1,width_cm=1,height_cm=1,estimated_price=1000,image=upload())
        name=variant.image.name
        variant.refresh_from_db(); self.assertEqual(variant.image.name,name)
        self.assertEqual(self.client.get(variant.image.url).status_code,200)
        Path(variant.image.path).unlink()
        self.assertEqual(self.client.get(variant.image.url).status_code,404)
    def test_runtime_storage_probe_and_volume_validation(self):
        call_command('check_media_storage',stdout=io.StringIO())
        self.assertEqual(list(Path(self.temp.name).iterdir()),[])
        with override_settings(IS_RAILWAY=True), patch.dict('os.environ', {'RAILWAY_VOLUME_MOUNT_PATH':''}):
            with self.assertRaises(CommandError):call_command('check_media_storage')
        with override_settings(IS_RAILWAY=True), patch.dict('os.environ', {'RAILWAY_VOLUME_MOUNT_PATH':self.temp.name}):
            call_command('check_media_storage',stdout=io.StringIO())
        with override_settings(IS_RAILWAY=True), patch.dict('os.environ', {'RAILWAY_VOLUME_MOUNT_PATH':'/unrelated'}):
            with self.assertRaises(CommandError):call_command('check_media_storage')
