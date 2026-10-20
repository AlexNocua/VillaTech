import struct
from io import BytesIO,StringIO
from zipfile import ZipFile
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command,CommandError
from django.contrib.auth import get_user_model
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from apps.landing.models import Product,CategoryProduct,Contact,ContactAttachment,ContactEmail
from .models import Entry,OperationalEmail,PrintingModel
from .workflow import approve_order,dispatch_emails
from .mesh_preview import mesh_preview

ASCII=b'solid model\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid model'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
MESH='<mesh><vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices><triangles><triangle v1="0" v2="1" v3="2"/></triangles></mesh>'
def archive(xml,extra=None):
    stream=BytesIO()
    with ZipFile(stream,'w') as z:
        z.writestr('3D/3dmodel.model',xml)
        for name,value in (extra or {}).items():z.writestr(name,value)
    return SimpleUploadedFile('model.3mf',stream.getvalue())

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',CONTACT_NOTIFICATION_EMAIL='owner@example.com',DEFAULT_FROM_EMAIL='sender@example.com',PUBLIC_SITE_URL='https://villatech.example')
class ModelsMailTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.tmp.name);self.override.enable();self.addCleanup(self.override.disable)
        self.staff=get_user_model().objects.create_user('modelstaff',is_staff=True);self.client.force_login(self.staff)
    def test_binary_and_ascii_stl(self):
        a=mesh_preview(SimpleUploadedFile('a.stl',ASCII));self.assertEqual(a['count'],1);self.assertEqual(a['bounds'],[[0,0,0],[1,1,0]])
        binary=b'solid binary'.ljust(80,b' ')+struct.pack('<I',1)+struct.pack('<12fH',0,0,1,0,0,0,1,0,0,0,1,0,0)
        b=mesh_preview(SimpleUploadedFile('b.stl',binary));self.assertEqual(a['triangles'],b['triangles'])
    def test_three_mf_build_transform_and_units(self):
        xml=f'<model xmlns="{NS}" unit="centimeter"><resources><object id="1">{MESH}</object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 2 3 4"/></build></model>'
        data=mesh_preview(archive(xml));self.assertEqual(data['bounds'],[[20,30,40],[30,40,40]])
    def test_three_mf_component_external_part(self):
        part=f'<model xmlns="{NS}"><resources><object id="2">{MESH}</object></resources><build/></model>'
        xml=f'<model xmlns="{NS}" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"><resources><object id="1"><components><component objectid="2" p:path="/3D/Objects/part.model" transform="1 0 0 0 1 0 0 0 1 5 0 0"/></components></object></resources><build><item objectid="1"/></build></model>'
        self.assertEqual(mesh_preview(archive(xml,{'3D/Objects/part.model':part}))['bounds'],[[5,0,0],[6,1,0]])
    def test_corrupt_and_cyclic_models_rejected(self):
        with self.assertRaises(ValidationError):mesh_preview(SimpleUploadedFile('bad.stl',b'bad'))
        xml=f'<model xmlns="{NS}"><resources><object id="1"><components><component objectid="1"/></components></object></resources><build><item objectid="1"/></build></model>'
        with self.assertRaises(ValidationError):mesh_preview(archive(xml))
    def test_library_upload_preview_download_and_private_access(self):
        response=self.client.post(reverse('management:model_library'),{'title':'Figura','description':'Modelo de prueba','file':SimpleUploadedFile('figura.stl',ASCII)})
        self.assertEqual(response.status_code,302);asset=PrintingModel.objects.get()
        preview=reverse('management:model_preview',args=['asset',asset.pk])
        self.assertEqual(Client().get(preview).status_code,302)
        self.assertEqual(self.client.get(preview).json()['count'],1)
        response=self.client.get(reverse('management:model_download',args=['asset',asset.pk]));self.assertIn('figura.stl',response['Content-Disposition']);response.close()
        self.assertContains(self.client.get(reverse('management:model_library')),'Figura')
    def test_library_lists_existing_product_and_customer_models(self):
        category=CategoryProduct.objects.create(category_name='3D')
        product=Product.objects.create(name='Base',mtm_category=category,price=1,print_model=SimpleUploadedFile('base.stl',ASCII),print_model_original_name='base.stl')
        contact=Contact.objects.create(client_name='Alex',email='client@example.com',telephone='1234567',service='otro',message='Referencia',file='')
        attachment=ContactAttachment.objects.create(contact=contact,file=SimpleUploadedFile('reference.stl',ASCII),original_name='reference.stl')
        page=self.client.get(reverse('management:model_library'));self.assertContains(page,'base.stl');self.assertContains(page,'reference.stl')
        self.assertEqual(self.client.get(reverse('management:model_preview',args=['reference',attachment.pk])).json()['count'],1)
        self.assertEqual(self.client.get(reverse('management:model_preview',args=['product',product.pk])).json()['count'],1)
    def test_new_order_owner_and_customer_not_duplicated(self):
        order=Entry.objects.create(kind='order',title='Pedido',amount=10000,customer_email='client@example.com',created_by=self.staff)
        with self.captureOnCommitCallbacks(execute=True):
            message=approve_order(order)
        dispatch_emails(message.pk)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox),['client@example.com','owner@example.com'])
        self.assertIn('/gestion/flujo/',mail.outbox[0].body)
        self.assertIsNone(approve_order(order));self.assertEqual(dispatch_emails(),0)
        self.assertEqual(OperationalEmail.objects.count(),2)
    def test_owner_notified_without_customer_email(self):
        order=Entry.objects.create(kind='order',title='Manual',amount=1000)
        with self.captureOnCommitCallbacks(execute=True):self.assertIsNone(approve_order(order))
        self.assertEqual(mail.outbox[0].to,['owner@example.com'])
    def test_owner_send_failure_can_retry_without_losing_order(self):
        order=Entry.objects.create(kind='order',title='Manual',amount=1000)
        with patch('django.core.mail.message.EmailMultiAlternatives.send',side_effect=OSError('offline')):
            with self.captureOnCommitCallbacks(execute=True):approve_order(order)
        message=OperationalEmail.objects.get();self.assertEqual(message.status,'failed')
        self.assertEqual(Entry.objects.count(),1);self.assertEqual(dispatch_emails(),1);self.assertEqual(dispatch_emails(),0)
    def test_contact_queue_is_visible_and_retry_command_handles_both(self):
        contact=Contact.objects.create(client_name='Alex',email='client@example.com',telephone='1234567',service='otro',message='Referencia',file='')
        ContactEmail.objects.create(contact=contact,audience='admin',subject='Nueva solicitud',recipient='',text='solicitud',html='<p>solicitud</p>',reply_to='client@example.com')
        self.assertContains(self.client.get(reverse('management:email_list')),'Nueva solicitud')
        call_command('process_email_queue',stdout=StringIO())
        self.assertEqual(mail.outbox[0].to,['owner@example.com']);call_command('process_email_queue',stdout=StringIO());self.assertEqual(len(mail.outbox),1)
    def test_check_configuration_does_not_reveal_credentials_or_send(self):
        output=StringIO()
        with override_settings(EMAIL_PROVIDER='gmail_api',EMAIL_BACKEND='apps.landing.gmail_backend.GmailAPIEmailBackend',GMAIL_CLIENT_ID='private-id',GMAIL_CLIENT_SECRET='private-secret',GMAIL_REFRESH_TOKEN='private-token'):
            call_command('check_mail_workflow',stdout=output)
        self.assertNotIn('private-secret',output.getvalue());self.assertEqual(len(mail.outbox),0)
        with override_settings(CONTACT_NOTIFICATION_EMAIL=''):
            with self.assertRaises(CommandError):call_command('check_mail_workflow',stdout=StringIO())

    def test_upload_storage_failure_keeps_form_and_logs_error(self):
        with patch('django.core.files.storage.FileSystemStorage._save',side_effect=OSError('disk full')),self.assertLogs('apps.management.model_library',level='ERROR'):
            response=self.client.post(reverse('management:model_library'),{'title':'Conservar título','description':'Conservar descripción','file':SimpleUploadedFile('figura.stl',ASCII)})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'No pudimos guardar el modelo')
        self.assertContains(response,'Conservar título')
        self.assertNotContains(response,'disk full')
        self.assertFalse(PrintingModel.objects.exists())

    def test_saving_model_does_not_parse_geometry(self):
        with patch('apps.management.model_library.solid_mesh_preview',side_effect=AssertionError('must not parse')):
            response=self.client.post(reverse('management:model_library'),{'title':'Archivo','file':SimpleUploadedFile('figura.stl',ASCII)})
        self.assertEqual(response.status_code,302)
        self.assertEqual(PrintingModel.objects.count(),1)

    def test_preview_deadline_returns_useful_error_and_preserves_file(self):
        from .mesh_preview import solid_mesh_preview
        with patch('apps.management.mesh_preview.PREVIEW_SECONDS',-1):
            with self.assertRaisesMessage(ValidationError,'Descarga el original'):
                solid_mesh_preview(SimpleUploadedFile('figura.stl',ASCII))

    def test_opinions_are_temporary_break_before_final_story_scenes(self):
        from pathlib import Path
        from django.conf import settings
        template=Path(settings.BASE_DIR_TEMPLATES)/'templates/landing/components/reviews.html'
        if not template.exists():
            template=Path(settings.BASE_DIR_TEMPLATES)/'landing/components/reviews.html'
        text=template.read_text()
        self.assertIn('data-story-break',text)
        self.assertNotIn('data-story-stop',text)
