import struct
from datetime import datetime,date,timezone as dtzone
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from .models import Entry,PrintingModel
from .mesh_preview import solid_mesh_preview
from .test_models_mail import archive,NS,MESH,ASCII

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CalendarTests(TestCase):
    def setUp(self):
        self.staff=get_user_model().objects.create_user('agenda',is_staff=True)
        self.client.force_login(self.staff)
        self.order=Entry.objects.create(kind='order',title='Pedido completo <script>x</script>',customer='Alex',amount=100,status='printing',estimated_delivery_date=date(2026,10,18))
        # 02:00 UTC is the previous day in Colombia.
        Entry.objects.filter(pk=self.order.pk).update(created_at=datetime(2026,10,16,2,tzinfo=dtzone.utc))
        self.url=reverse('management:calendar')
    def test_staff_only(self):
        self.assertEqual(Client().get(self.url).status_code,302)
        self.client.force_login(get_user_model().objects.create_user('ordinary'))
        self.assertEqual(self.client.get(self.url).status_code,403)
    def test_created_day_uses_local_timezone_and_links_detail(self):
        response=self.client.get(self.url,{'view':'day','date':'2026-10-15'})
        self.assertEqual([e['id'] for e in response.context['selected_events']],[self.order.pk])
        self.assertContains(response,reverse('management:workflow_detail',args=[self.order.pk]))
        self.assertNotContains(response,'<script>x</script>')
        self.assertEqual(self.client.get(self.url,{'view':'day','date':'2026-10-16'}).context['total'],0)
    def test_delivery_and_payment_filters(self):
        paid=Entry.objects.create(kind='order',title='Pagado',amount=100,paid_amount=100,status='pending',estimated_delivery_date=date(2026,10,18))
        Entry.objects.create(kind='quote',title='Cotización',amount=100,estimated_delivery_date=date(2026,10,18))
        response=self.client.get(self.url,{'view':'day','date':'2026-10-18','basis':'delivery','payment':'paid'})
        self.assertEqual([e['id'] for e in response.context['events']],[paid.pk])
        response=self.client.get(self.url,{'view':'week','date':'2026-10-18','basis':'delivery','payment':'pending','status':'printing'})
        self.assertEqual([e['id'] for e in response.context['events']],[self.order.pk])
        self.assertIn('payment=pending',response.context['next_url']);self.assertIn('status=printing',response.context['next_url'])
    def test_month_and_week_boundaries_and_navigation(self):
        response=self.client.get(self.url,{'view':'month','date':'2026-12-31'})
        self.assertIn('2027-01-01',response.context['next_url'])
        response=self.client.get(self.url,{'view':'week','date':'2026-10-18'})
        self.assertEqual(response.context['rows'][0][0]['date'],date(2026,10,12));self.assertEqual(len(response.context['rows'][0]),7)
        response=self.client.get(self.url,{'view':'month','date':'2028-02-29'})
        self.assertTrue(any(day['date']==date(2028,2,29) for row in response.context['rows'] for day in row))
    def test_undated_and_closed_sales_are_visible_in_correct_places(self):
        Entry.objects.create(kind='order',title='Sin fecha',amount=1)
        sale=Entry.objects.create(kind='sale',title='Entregado',amount=50,estimated_delivery_date=date(2026,10,18))
        response=self.client.get(self.url,{'view':'month','date':'2026-10-18','basis':'delivery'})
        self.assertEqual(response.context['undated'],1)
        self.assertIn(sale.pk,[e['id'] for e in response.context['events']])
        self.assertContains(response,'due=undated')
    def test_invalid_values_fall_back_and_calendar_never_writes(self):
        before=Entry.objects.count()
        with patch('apps.management.calendar_views.timezone.localdate',return_value=date(2026,10,15)):
            response=self.client.get(self.url,{'date':'9999-12-31','view':'invalid','basis':'invalid'})
        self.assertEqual(response.status_code,200);self.assertEqual(response.context['selected'],date(2026,10,15));self.assertEqual(response.context['mode'],'month')
        self.assertEqual(self.client.post(self.url).status_code,405);self.assertEqual(Entry.objects.count(),before)

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SolidPreviewTests(TestCase):
    def test_dense_stl_retains_all_faces_instead_of_thinning(self):
        number=12005
        triangle=struct.pack('<12fH',0,0,1,0,0,0,1,0,0,0,1,0,0)
        source=b'VT'.ljust(80,b' ')+struct.pack('<I',number)+triangle*number
        with solid_mesh_preview(SimpleUploadedFile('dense.stl',source)) as result:
            data=result.read()
        self.assertEqual(data[:4],b'VTM1');self.assertEqual(struct.unpack_from('<I',data,4)[0],number)
        self.assertEqual(len(data),64+36*number);self.assertEqual(struct.unpack_from('<9f',data,64),(0,0,0,1,0,0,0,1,0))
    def test_three_mf_preserves_transforms_and_mm_bounds(self):
        xml=f'<model xmlns="{NS}" unit="centimeter"><resources><object id="1">{MESH}</object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 2 3 4"/></build></model>'
        with solid_mesh_preview(archive(xml)) as result:data=result.read()
        self.assertEqual(struct.unpack_from('<6d',data,8),(20,30,40,30,40,40));self.assertEqual(struct.unpack_from('<I',data,56)[0],1)
    def test_invalid_and_limit_fail_cleanly(self):
        with self.assertRaises(ValidationError):solid_mesh_preview(SimpleUploadedFile('broken.stl',b'bad'))
        with patch('apps.management.mesh_preview.MAX_TRIANGLES',0):
            with self.assertRaises(ValidationError):solid_mesh_preview(SimpleUploadedFile('a.stl',ASCII))
    def test_binary_preview_private_and_original_unchanged(self):
        with TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            staff=get_user_model().objects.create_user('solid_staff',is_staff=True);self.client.force_login(staff)
            asset=PrintingModel.objects.create(title='Superficie',created_by=staff,file=SimpleUploadedFile('a.stl',ASCII),original_name='a.stl')
            url=reverse('management:model_preview',args=['asset',asset.pk])
            self.assertEqual(Client().get(url,HTTP_ACCEPT='application/octet-stream').status_code,302)
            response=self.client.get(url,HTTP_ACCEPT='application/octet-stream');data=b''.join(response.streaming_content);response.close()
            self.assertEqual(data[:4],b'VTM1');self.assertIn('private',response['Cache-Control']);self.assertIn('no-store',response['Cache-Control'])
            with asset.file.open('rb') as original:self.assertEqual(original.read(),ASCII)
            self.assertEqual(self.client.get(url).json()['count'],1)
