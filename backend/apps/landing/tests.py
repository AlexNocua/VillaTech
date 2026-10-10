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
        self.assertEqual(entry.contact.telephone,self.data['phone'])
        self.assertEqual(Contact._meta.get_field('telephone').get_internal_type(),'CharField')
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
        self.assertContains(self.client.get(reverse('management:quote_detail',args=[entry.pk])),'Descargar archivo')
        self.assertEqual(self.client.get(reverse('management:quote_pdf',args=[entry.pk])).status_code,400)
        self.assertEqual(self.client.post(reverse('management:transition',args=[entry.pk,'order'])).status_code,400)
    def test_filters_and_quote_order_transition_preserve_source_and_contact(self):
        self.submit(); web = Entry.objects.get()
        manual = Entry.objects.create(kind='order',title='Manual',amount=100,created_by=self.staff,status='ready')
        self.client.force_login(self.staff)
        response = self.client.get('/gestion/cotizaciones/?source=web&status=draft')
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

class GmailPasswordTests(TestCase):
    @override_settings(EMAIL_HOST='smtp.gmail.com',EMAIL_HOST_PASSWORD='abcd efgh ijkl mnop',EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',DEFAULT_FROM_EMAIL='team@example.com')
    def test_application_password_normalized_and_transport_failure_saved(self):
        from .notifications import dispatch_contact_emails
        from django.core.mail import get_connection
        contact=Contact.objects.create(client_name='Cliente',telephone=3204504722,email='client@example.com',service='otro',message='Prueba',file='')
        ContactEmail.objects.create(contact=contact,audience='customer',recipient=contact.email,subject='Prueba',text='Texto',html='<p>Texto</p>')
        connection=get_connection()
        with patch('apps.landing.notifications.get_connection',return_value=connection), patch.object(connection,'send_messages',return_value=1):
            self.assertEqual(dispatch_contact_emails(contact.pk),1)
        self.assertEqual(connection.password,'abcdefghijklmnop')

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',CONTACT_NOTIFICATION_EMAIL='team@example.com',PUBLIC_SITE_URL='https://example.com')
class ContactValidationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.data={'name':'Nombre conservado','phone':'+57 320 450 4722','email':'cliente@example.com','service':'otro','message':'Texto conservado','privacy_consent':'accepted'}
    def test_json_field_errors_do_not_save(self):
        self.data['email']='incorrecto';self.data['phone']='abc'
        response=self.client.post('/submit',self.data,HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,400)
        self.assertIn('email',response.json()['errors']);self.assertIn('phone',response.json()['errors'])
        self.assertFalse(Contact.objects.exists())
    def test_html_error_retains_values(self):
        self.data['email']='incorrecto'
        response=self.client.post('/submit',self.data)
        self.assertEqual(response.status_code,400)
        self.assertContains(response,'Nombre conservado',status_code=400)
        self.assertContains(response,'Texto conservado',status_code=400)
        self.assertContains(response,'Introduce un correo válido',status_code=400)
        self.assertContains(response,'vt-toast__brand',status_code=400)
        self.assertContains(response,'Ocurrió un problema',status_code=400)
        self.assertNotContains(response,'form-alert--error',status_code=400)
    def test_internal_error_is_generic_and_logged(self):
        with patch('apps.landing.views.Contact.objects.create',side_effect=RuntimeError('private database detail')),self.assertLogs('apps.landing.views',level='ERROR'):
            response=self.client.post('/submit',self.data,HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,500)
        self.assertNotIn('private database detail',response.content.decode())
        self.assertEqual(response.json()['errors'],{})
    def test_success_json(self):
        with self.captureOnCommitCallbacks(execute=True):response=self.client.post('/submit',self.data,HTTP_ACCEPT='application/json')
        self.assertTrue(response.json()['ok']);self.assertEqual(Contact.objects.count(),1)
    def test_file_errors_attached_to_file_field(self):
        self.data['reference_files']=SimpleUploadedFile('mal.exe',b'invalid')
        response=self.client.post('/submit',self.data,HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,400)
        self.assertIn('reference_files',response.json()['errors'])

class MailDiagnosticTests(TestCase):
    def test_network_and_authentication_are_distinguished_without_secrets(self):
        import errno,smtplib
        from .mail_diagnostics import mail_error_summary,safe_error_code
        network=OSError(errno.ENETUNREACH,'secret provider body')
        auth=smtplib.SMTPAuthenticationError(535,b'secret provider body')
        self.assertIn('red SMTP',mail_error_summary(network))
        self.assertIn('contraseña de aplicación',mail_error_summary(auth))
        self.assertNotIn('secret',mail_error_summary(auth))
        self.assertNotIn('secret',safe_error_code(network))
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='smtp.gmail.com',EMAIL_HOST_USER='test@example.com',EMAIL_HOST_PASSWORD='abcd efgh')
    @patch('apps.landing.management.commands.check_email_connection.get_connection')
    def test_connection_check_does_not_send(self,mocked):
        from django.core.management import call_command
        from io import StringIO
        mocked.return_value.password='abcd efgh'
        output=StringIO();call_command('check_email_connection',stdout=output)
        mocked.return_value.open.assert_called_once()
        mocked.return_value.send_messages.assert_not_called()
        self.assertEqual(mocked.return_value.password,'abcdefgh')
        self.assertNotIn('abcdefgh',output.getvalue())

@override_settings(GMAIL_CLIENT_ID='test-client',GMAIL_CLIENT_SECRET='test-secret',GMAIL_REFRESH_TOKEN='test-refresh',EMAIL_TIMEOUT=10)
class GmailAPITransportTests(TestCase):
    @patch('apps.landing.gmail_backend.urlopen')
    def test_refresh_and_send_preserve_mime(self,opened):
        import base64
        from email import message_from_bytes
        from django.core.mail import EmailMultiAlternatives
        from .gmail_backend import GmailAPIEmailBackend
        responses=[]
        for value in [{'access_token':'test-access'},{'id':'accepted'}]:
            mock=MagicMock();mock.__enter__.return_value.read.return_value=json.dumps(value).encode();responses.append(mock)
        opened.side_effect=responses
        message=EmailMultiAlternatives('Asunto','Texto','team@example.com',['client@example.com'],reply_to=['reply@example.com'])
        message.attach_alternative('<p>HTML</p>','text/html')
        backend=GmailAPIEmailBackend()
        self.assertEqual(backend.send_messages([message]),1)
        request=opened.call_args.args[0]
        self.assertEqual(request.full_url,'https://gmail.googleapis.com/gmail/v1/users/me/messages/send')
        mime=message_from_bytes(base64.urlsafe_b64decode(json.loads(request.data)['raw']))
        self.assertEqual(mime['Reply-To'],'reply@example.com')
        self.assertEqual(mime['To'],'client@example.com')
        self.assertTrue(mime.is_multipart())
        backend.close();self.assertIsNone(backend.access_token)
    @patch('apps.landing.gmail_backend.urlopen')
    def test_google_error_does_not_leak_secrets(self,opened):
        from urllib.error import HTTPError
        from .gmail_backend import GmailAPIEmailBackend,GmailAPIError
        opened.side_effect=HTTPError('https://oauth2.googleapis.com/token',400,'private provider data',{},None)
        with self.assertRaises(GmailAPIError) as caught:GmailAPIEmailBackend().open()
        self.assertNotIn('private provider data',str(caught.exception))
        self.assertIn('HTTP 400',str(caught.exception))
    @override_settings(GMAIL_REFRESH_TOKEN='')
    def test_missing_configuration_is_clear(self):
        from .gmail_backend import GmailAPIEmailBackend,GmailAPIError
        with self.assertRaises(GmailAPIError):GmailAPIEmailBackend().open()
