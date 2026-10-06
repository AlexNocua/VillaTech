import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Contact, ContactEmail, ContactAttachment
from .notifications import dispatch_contact_emails
from apps.management.models import Entry

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_NOTIFICATION_EMAIL='team@example.com',DEFAULT_FROM_EMAIL='VillaTech <sender@example.com>',
    PUBLIC_SITE_URL='https://villatech.example')
class ContactWorkflowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.temp.name)
        self.media.enable(); self.addCleanup(self.media.disable)
        self.staff = get_user_model().objects.create_user('team',is_staff=True)
        self.data = {'name':'Cliente de prueba','phone':'+57 320 450 4722','email':'client@example.com',
            'service':'impresion-3d','message':'Me interesa cotizar una figura <script>alert(1)</script>',
            'privacy_consent':'accepted'}
    def submit(self):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post('/submit',self.data)
    def test_public_request_creates_one_draft_and_two_separate_emails(self):
        self.submit()
        entry = Entry.objects.get()
        self.assertEqual((entry.kind,entry.status,entry.source),('quote','draft','web'))
        self.assertIsNone(entry.created_by_id)
        self.assertEqual(entry.contact,Contact.objects.get())
        self.assertEqual(entry.customer_phone,self.data['phone'])
        self.assertEqual(len(mail.outbox),2)
        self.assertEqual(mail.outbox[0].to,['client@example.com'])
        self.assertEqual(mail.outbox[1].to,['team@example.com'])
        self.assertEqual(mail.outbox[1].reply_to,['client@example.com'])
        self.assertNotIn('/gestion/',mail.outbox[0].body)
        self.assertIn('/gestion/',mail.outbox[1].body)
        self.assertNotIn('<script>',mail.outbox[1].alternatives[0].content)
        self.assertEqual(ContactEmail.objects.filter(status='sent').count(),2)
        self.assertEqual(dispatch_contact_emails(),0)
        self.assertEqual(len(mail.outbox),2)
    def test_failure_retains_request_and_retries_only_failed_message(self):
        with patch('apps.landing.notifications.EmailMultiAlternatives.send',side_effect=[OSError('fail'),1]):
            self.submit()
        self.assertEqual(Entry.objects.count(),1)
        self.assertEqual(ContactEmail.objects.filter(status='failed').count(),1)
        self.assertEqual(dispatch_contact_emails(),1)
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(ContactEmail.objects.filter(status='sent').count(),2)
    def test_invalid_request_has_no_draft_or_email(self):
        self.data.pop('privacy_consent')
        self.submit()
        self.assertEqual(Entry.objects.count(),0)
        self.assertEqual(ContactEmail.objects.count(),0)
    def test_download_private_and_pdf_unavailable_until_priced(self):
        self.data['reference_files']=SimpleUploadedFile('pieza.stl',b'solid model\nendsolid model')
        self.submit()
        attachment = ContactAttachment.objects.get(); entry = Entry.objects.get()
        path = reverse('management:contact_attachment',args=[attachment.pk])
        self.assertEqual(self.client.get(path).status_code,302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(path).status_code,200)
        self.assertContains(self.client.get(reverse('management:quote_detail',args=[entry.pk])),'Descargar referencia')
        self.assertEqual(self.client.get(reverse('management:quote_pdf',args=[entry.pk])).status_code,400)
        self.assertEqual(self.client.post(reverse('management:transition',args=[entry.pk,'order'])).status_code,400)
    def test_filters_and_quote_order_transition_preserve_source_and_contact(self):
        self.submit(); web = Entry.objects.get()
        manual = Entry.objects.create(kind='order',title='Manual',amount=100,created_by=self.staff,status='ready')
        self.client.force_login(self.staff)
        response = self.client.get('/gestion/pedidos/?source=web&status=draft')
        self.assertEqual(list(response.context['page']),[web])
        response = self.client.get('/gestion/pedidos/?source=manual&status=ready')
        self.assertEqual(list(response.context['page']),[manual])
        self.assertEqual(self.client.get('/gestion/cotizaciones/').context['page'].paginator.count,1)
        response = self.client.post(reverse('management:edit',args=['quote',web.pk]),{
            'title':web.title,'description':web.description,'customer':web.customer,'customer_email':web.customer_email,
            'customer_phone':web.customer_phone,'amount':'125000','logo_theme':'light',
            'items-TOTAL_FORMS':'0','items-INITIAL_FORMS':'0','items-MIN_NUM_FORMS':'0','items-MAX_NUM_FORMS':'30'})
        self.assertEqual(response.status_code,302)
        web.refresh_from_db(); self.assertEqual(web.status,'quoted'); self.assertTrue(web.quotation_pdf)
        self.assertEqual(self.client.post(reverse('management:transition',args=[web.pk,'order'])).status_code,302)
        web.refresh_from_db()
        self.assertEqual((web.kind,web.status,web.source),('order','pending','web'))
        self.assertIsNotNone(web.contact_id)
        self.assertEqual(Entry.objects.count(),2)
        self.assertEqual(self.client.post(reverse('management:transition',args=[web.pk,'order'])).status_code,400)
    def test_missing_admin_address_can_be_configured_and_retried(self):
        with override_settings(CONTACT_NOTIFICATION_EMAIL=''):
            self.submit()
        self.assertEqual(ContactEmail.objects.get(audience='admin').status,'failed')
        self.client.force_login(self.staff)
        self.client.post(reverse('management:retry_notifications',args=[Entry.objects.get().pk]))
        self.assertEqual(ContactEmail.objects.get(audience='admin').recipient,'team@example.com')
        self.assertEqual(ContactEmail.objects.filter(status='sent').count(),2)

class ResendTransportTests(TestCase):
    @override_settings(RESEND_API_KEY='test-placeholder',EMAIL_TIMEOUT=10)
    @patch('apps.landing.email_backend.urlopen')
    def test_https_payload(self,opened):
        from .email_backend import ResendEmailBackend
        from django.core.mail import EmailMultiAlternatives
        opened.return_value.__enter__.return_value.read.return_value=b'{"id":"test-id"}'
        message = EmailMultiAlternatives('Subject','Text','sender@example.com',['client@example.com'],
            reply_to=['team@example.com'],headers={'Idempotency-Key':'request-1'})
        message.attach_alternative('<p>Text</p>','text/html')
        self.assertEqual(ResendEmailBackend().send_messages([message]),1)
        request=opened.call_args.args[0];payload=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.resend.com/emails')
        self.assertEqual(payload['reply_to'],['team@example.com'])
        self.assertEqual(payload['html'],'<p>Text</p>')
    @override_settings(RESEND_API_KEY='')
    def test_missing_api_key_fails(self):
        from .email_backend import ResendEmailBackend
        from django.core.mail import EmailMessage
        with self.assertRaises(ValueError):
            ResendEmailBackend().send_messages([EmailMessage('Subject','Text',to=['client@example.com'])])

class HistoricalImportTests(TestCase):
    def test_historical_requests_import_once_without_sending_mail(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        from types import SimpleNamespace
        contact=Contact.objects.create(client_name='Anterior',telephone=3204504722,email='old@example.com',
            service='otro',message='Solicitud anterior',file='')
        migration=import_module('apps.management.migrations.0009_import_existing_web_requests')
        editor=SimpleNamespace(connection=connection)
        migration.import_requests(apps,editor)
        migration.import_requests(apps,editor)
        self.assertEqual(Entry.objects.filter(contact=contact).count(),1)
        self.assertEqual(ContactEmail.objects.count(),0)
