from io import BytesIO
from PIL import Image
from tempfile import TemporaryDirectory
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from .contact_forms import validate_reference
from .models import ContactAttachment
from apps.management.models import Entry

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ReferenceMediaTests(TestCase):
    def setUp(self):
        cache.clear();self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.tmp.name);self.override.enable();self.addCleanup(self.override.disable)
        self.staff=get_user_model().objects.create_user('files-staff',is_staff=True)
        self.data=dict(name='Cliente',phone='3204504722',email='client@example.com',service='impresion-3d',
            message='Referencia de mi proyecto',privacy_consent='accepted')
    def video(self):return SimpleUploadedFile('referencia.mp4',b'\x00\x00\x00\x18ftypisom'+b'\x00'*100,content_type='video/mp4')
    def submit(self, files):
        return self.client.post('/submit',{**self.data,'reference_files':files},HTTP_ACCEPT='application/json')
    def test_size_100mb_allowed_and_larger_rejected(self):
        file=self.video();file.size=100*1024*1024;validate_reference(file)
        self.assertEqual(file.tell(),0)
        file.size+=1
        with self.assertRaises(ValidationError):validate_reference(file)
    def test_invalid_video_content_rejected(self):
        with self.assertRaises(ValidationError):validate_reference(SimpleUploadedFile('fake.mp4',b'not a video'))
        self.assertEqual(self.submit([SimpleUploadedFile('bad.webm',b'bad')]).status_code,400)
        self.assertEqual(ContactAttachment.objects.count(),0)
    def test_video_upload_saved_private_and_embedded_in_order(self):
        self.assertEqual(self.submit([self.video()]).status_code,200)
        attachment=ContactAttachment.objects.get();entry=Entry.objects.get()
        self.assertEqual(attachment.original_name,'referencia.mp4')
        url=reverse('management:contact_attachment',args=[attachment.pk])+'?preview=1'
        self.assertEqual(Client().get(url).status_code,302)
        self.client.force_login(self.staff)
        page=self.client.get(reverse('management:workflow_detail',args=[entry.pk]))
        self.assertContains(page,'<video');self.assertContains(page,'referencia.mp4')
        response=self.client.get(url);self.assertEqual(response['Content-Type'],'video/mp4')
        self.assertIn('no-store',response['Cache-Control']);response.close()
        response=self.client.get(url,HTTP_RANGE='bytes=8-19')
        self.assertEqual(response.status_code,206);self.assertEqual(b''.join(response.streaming_content),b'isom'+b'\x00'*8)
        self.assertEqual(response['Content-Length'],'12')
        self.assertEqual(self.client.get(url,HTTP_RANGE='bytes=999-1000').status_code,416)
        suffix=self.client.get(url,HTTP_RANGE='bytes=-4');self.assertEqual(b''.join(suffix.streaming_content),b'\x00'*4)
    def test_images_preview_and_documents_download(self):
        data=BytesIO();Image.new('RGB',(2,2)).save(data,format='PNG')
        self.submit([SimpleUploadedFile('foto.png',data.getvalue()),SimpleUploadedFile('pieza.stl',b'solid\nendsolid')])
        self.client.force_login(self.staff);entry=Entry.objects.get()
        page=self.client.get(reverse('management:workflow_detail',args=[entry.pk]))
        self.assertContains(page,'foto.png');self.assertContains(page,'pieza.stl');self.assertContains(page,'?preview=1')
        image=ContactAttachment.objects.get(original_name='foto.png')
        response=self.client.get(reverse('management:contact_attachment',args=[image.pk])+'?preview=1')
        self.assertEqual(response['Content-Type'],'image/png');response.close()
        doc=ContactAttachment.objects.get(original_name='pieza.stl')
        response=self.client.get(reverse('management:contact_attachment',args=[doc.pk])+'?preview=1')
        self.assertIn('attachment',response['Content-Disposition']);response.close()
    def test_webm_and_mov_and_file_count(self):
        validate_reference(SimpleUploadedFile('v.webm',b'\x1a\x45\xdf\xa3'+b'\x00'*12))
        validate_reference(SimpleUploadedFile('v.mov',b'\x00\x00\x00\x18ftypqt  '+b'\x00'*12))
        self.assertEqual(self.submit([self.video() for _ in range(6)]).status_code,400)
    def test_product_model_upload_download_and_preserve_on_edit(self):
        from .models import CategoryProduct,Product
        category=CategoryProduct.objects.create(category_name='Modelos')
        self.client.force_login(self.staff)
        payload={'name':'Soporte','mtm_category':category.pk,'price':20000,'is_active':'on',
            'print_model':SimpleUploadedFile('soporte.stl',b'solid soporte\nendsolid soporte')}
        self.assertEqual(self.client.post(reverse('management:product'),payload).status_code,302)
        product=Product.objects.get();self.assertEqual(product.print_model_original_name,'soporte.stl')
        self.assertTrue(product.print_model.storage.exists(product.print_model.name))
        self.assertTrue(product.print_model.name.startswith('private/'))
        url=reverse('management:product_model',args=[product.pk])
        self.assertEqual(Client().get(url).status_code,302)
        response=self.client.get(url)
        self.assertIn('soporte.stl',response['Content-Disposition']);response.close()
        saved=product.print_model.name
        self.client.post(reverse('management:product_edit',args=[product.pk]),{'name':'Soporte actualizado','mtm_category':category.pk,'price':22000,'is_active':'on'})
        product.refresh_from_db();self.assertEqual(product.print_model.name,saved)
        self.assertContains(self.client.get(reverse('management:products')),'Descargar modelo')
        self.assertContains(self.client.get(reverse('management:product_edit',args=[product.pk])),'soporte.stl')
    def test_product_model_validates_format_and_limit(self):
        from .validators import validate_print_model
        file=SimpleUploadedFile('pieza.3mf',b'PK');file.size=100*1024*1024
        validate_print_model(file);file.size+=1
        with self.assertRaises(ValidationError):validate_print_model(file)
        with self.assertRaises(ValidationError):validate_print_model(SimpleUploadedFile('mal.exe',b'x'))
    def test_combined_upload_limit_is_200mb(self):
        from django.test import RequestFactory
        from django.utils.datastructures import MultiValueDict
        from .views import contact_form_action
        files=[self.video() for _ in range(3)]
        for file in files:file.size=75*1024*1024
        request=RequestFactory().post('/submit',self.data,HTTP_ACCEPT='application/json')
        request.POST  # Parse form fields before replacing the upload fixture.
        request._files=MultiValueDict({'reference_files':files})
        response=contact_form_action(request)
        self.assertEqual(response.status_code,400)
        self.assertIn(b'200 MB',response.content)
        self.assertEqual(ContactAttachment.objects.count(),0)
