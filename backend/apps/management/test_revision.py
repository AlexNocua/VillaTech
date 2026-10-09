from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
import tempfile
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import Entry, Payment, OperationalEmail, CustomerIssue, QuoteItem
from .quotations import approval_token, entry_from_token, expire_quotes, send_quotation
from .workflow import dispatch_emails


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_NOTIFICATION_EMAIL='owner@example.com', DEFAULT_FROM_EMAIL='sender@example.com',
    PUBLIC_SITE_URL='https://villatech.example')
class ConfirmationRevisionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = get_user_model().objects.create_user('revision',is_staff=True)
        self.client.force_login(self.staff)
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.temp.name);self.override.enable();self.addCleanup(self.override.disable)

    def quote(self, **extra):
        data=dict(kind='quote',status='quoted',title='Figura personalizada',customer='Alex',
            customer_email='client@example.com',amount=10000,unit_price=5000,quantity=2,created_by=self.staff)
        data.update(extra)
        return Entry.objects.create(**data)

    def send(self, entry):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('management:send_quotation',args=[entry.pk]))
        entry.refresh_from_db()
        return approval_token(entry)

    def test_old_signature_does_not_override_active_database_window(self):
        entry=self.quote();self.send(entry)
        import time
        with patch('django.core.signing.time.time',return_value=time.time()-72*3600):
            old_token=approval_token(entry)
        self.assertEqual(entry_from_token(old_token).pk,entry.pk)
        url=reverse('management:customer_quote',args=[old_token])
        response=Client().get(url)
        self.assertContains(response,'Confirmar mi pedido')
        self.assertNotContains(response,'Se cumplieron las 48 horas')
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(Client().post(url,{'accept':'yes'}).status_code,302)
        entry.refresh_from_db();self.assertEqual(entry.kind,'order')

    def test_failed_send_does_not_start_or_exhaust_window(self):
        entry=self.quote()
        with patch('django.core.mail.message.EmailMultiAlternatives.send',side_effect=OSError('offline')):
            self.send(entry)
        self.assertIsNone(entry.quote_sent_at);self.assertIsNone(entry.quote_expires_at)
        self.assertEqual(expire_quotes(),0)
        later=timezone.now()+timedelta(days=4)
        with patch('apps.management.workflow.timezone.now',return_value=later):
            self.assertEqual(dispatch_emails(),1)
        entry.refresh_from_db()
        self.assertEqual(entry.quote_sent_at,later)
        self.assertEqual(entry.quote_expires_at,later+timedelta(hours=48))
        self.assertIn('Válida hasta',mail.outbox[-1].body)

    def test_window_boundary_allows_before_and_rejects_at_expiry(self):
        entry=self.quote();token=self.send(entry);url=reverse('management:customer_quote',args=[token])
        with patch('apps.management.quotations.timezone.now',return_value=entry.quote_expires_at-timedelta(seconds=1)):
            self.assertContains(Client().get(url),'Confirmar mi pedido')
        with patch('apps.management.quotations.timezone.now',return_value=entry.quote_expires_at):
            response=Client().post(url,{'accept':'yes'})
        self.assertContains(response,'Se cumplieron las 48 horas')
        self.assertContains(response,'Reportar problema')
        entry.refresh_from_db();self.assertEqual(entry.kind,'quote')

    def test_resend_rotates_url_reopens_expired_and_invalidates_old(self):
        entry=self.quote();old=self.send(entry);nonce=str(entry.approval_nonce)
        Entry.objects.filter(pk=entry.pk).update(status='expired',quote_expires_at=timezone.now()-timedelta(days=1))
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post(reverse('management:resend_quotation',args=[entry.pk]),{'version':nonce})
        self.assertEqual(response.status_code,302)
        entry.refresh_from_db();new=approval_token(entry)
        self.assertNotEqual(str(entry.approval_nonce),nonce)
        self.assertEqual(entry.status,'sent')
        self.assertEqual(entry.quote_expires_at-entry.quote_sent_at,timedelta(hours=48))
        self.assertContains(Client().get(reverse('management:customer_quote',args=[old])),'fue reemplazado')
        self.assertContains(Client().get(reverse('management:customer_quote',args=[new])),'Confirmar mi pedido')
        self.assertEqual(len(mail.outbox),2)
        self.client.post(reverse('management:resend_quotation',args=[entry.pk]),{'version':nonce})
        self.assertEqual(OperationalEmail.objects.filter(event_key__startswith='quote:').count(),2)

    def test_resend_failure_retains_fresh_version_for_retry(self):
        entry=self.quote();self.send(entry)
        with patch('django.core.mail.message.EmailMultiAlternatives.send',side_effect=OSError('offline')):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse('management:resend_quotation',args=[entry.pk]))
        entry.refresh_from_db();self.assertIsNone(entry.quote_expires_at)
        self.assertEqual(entry.emails.filter(status='failed').count(),1)
        with self.captureOnCommitCallbacks(execute=True):self.client.post(reverse('management:send_quotation',args=[entry.pk]))
        entry.refresh_from_db();self.assertIsNotNone(entry.quote_expires_at)
        self.assertEqual(entry.emails.filter(event_key__startswith='quote:').count(),2)

    def test_bad_resend_rolls_back_nonce_and_original_link(self):
        entry=self.quote();self.send(entry);nonce=entry.approval_nonce
        entry.customer_email='';entry.save()
        self.client.post(reverse('management:resend_quotation',args=[entry.pk]))
        entry.refresh_from_db();self.assertEqual(entry.approval_nonce,nonce);self.assertEqual(entry.status,'sent')

    def test_issue_records_comment_sends_only_to_owner_and_escapes_html(self):
        entry=self.quote();token=self.send(entry)
        url=reverse('management:customer_issue',args=[token])
        public=Client(enforce_csrf_checks=True);self.assertEqual(public.get(url).status_code,200)
        with self.captureOnCommitCallbacks(execute=True):
            response=public.post(url,{'customer_email':'reply@example.com','comment':'Me aparece <script>error</script>. Necesito otra URL.',
                'csrfmiddlewaretoken':public.cookies['csrftoken'].value})
        self.assertEqual(response.status_code,302)
        issue=CustomerIssue.objects.get();self.assertEqual(issue.entry,entry)
        self.assertEqual(mail.outbox[-1].to,['owner@example.com'])
        self.assertIn('reply@example.com',mail.outbox[-1].body)
        self.assertNotIn('<script>',mail.outbox[-1].alternatives[0].content)
        self.assertContains(self.client.get(reverse('management:workflow_detail',args=[entry.pk])),'Reportes del cliente')
        entry.refresh_from_db();self.assertEqual(entry.kind,'quote')

    def test_issue_invalid_fields_keep_entered_comment(self):
        entry=self.quote();token=self.send(entry)
        response=Client().post(reverse('management:customer_issue',args=[token]),{'customer_email':'bad','comment':'No puedo confirmar la cotización.'})
        self.assertContains(response,'No puedo confirmar la cotización.')
        self.assertEqual(CustomerIssue.objects.count(),0)

    def test_issue_csrf_and_rate_limit_are_enforced(self):
        entry=self.quote();token=self.send(entry);url=reverse('management:customer_issue',args=[token])
        self.assertEqual(Client(enforce_csrf_checks=True).post(url,{'comment':'Hay un error'}).status_code,403)
        with self.captureOnCommitCallbacks(execute=True):
            for i in range(6):Client().post(url,{'comment':f'Problema de confirmación {i}'})
        self.assertEqual(CustomerIssue.objects.count(),5)
        self.assertEqual(len(mail.outbox),6)  # quotation + five owner reports

    def test_stale_and_invalid_links_can_report_without_approving(self):
        entry=self.quote();old=self.send(entry)
        with self.captureOnCommitCallbacks(execute=True):self.client.post(reverse('management:resend_quotation',args=[entry.pk]))
        with self.captureOnCommitCallbacks(execute=True):
            Client().post(reverse('management:customer_issue',args=[old]),{'comment':'El enlace anterior dejó de funcionar.'})
            Client().post(reverse('management:customer_issue',args=['invalid']),{'comment':'No puedo abrir la confirmación.'})
        self.assertEqual(CustomerIssue.objects.filter(entry=entry).count(),1)
        self.assertEqual(CustomerIssue.objects.filter(entry__isnull=True).count(),1)
        entry.refresh_from_db();self.assertEqual(entry.kind,'quote')

    def test_delivery_settles_remainder_preserves_deposits_and_counts_once(self):
        entry=self.quote(kind='order',status='ready',paid_amount=3000,approved_at=timezone.now())
        Payment.objects.create(entry=entry,amount=3000,created_by=self.staff)
        before=self.client.get('/gestion/').context['sales']
        path=reverse('management:update_delivery',args=[entry.pk])
        with self.captureOnCommitCallbacks(execute=True):self.client.post(path,{'status':'delivered'})
        entry.refresh_from_db()
        self.assertEqual((entry.kind,entry.status,entry.paid_amount,entry.outstanding),('sale','sold',10000,0))
        self.assertEqual(entry.delivery_settled_amount,7000)
        self.assertEqual(entry.payments.count(),1)
        self.assertEqual(self.client.get('/gestion/').context['sales'],before)
        self.assertEqual(self.client.get('/gestion/').context['collected'],10000)
        self.assertEqual(self.client.get('/gestion/').context['pending'],0)
        self.assertEqual(self.client.get('/gestion/pedidos/').context['page'].paginator.count,0)
        self.assertEqual(self.client.get('/gestion/ventas/').context['page'].paginator.count,1)
        self.client.post(path,{'status':'delivered'});self.assertEqual(entry.emails.count(),1)
        self.assertIn('Cierre automático',mail.outbox[-1].body)
        self.assertContains(Client().get(reverse('management:customer_quote',args=[approval_token(entry)])),'Tu pedido está confirmado')

    def test_delete_requires_confirmation_and_removes_related_records(self):
        entry=self.quote(kind='order',paid_amount=2000)
        Payment.objects.create(entry=entry,amount=2000,created_by=self.staff)
        QuoteItem.objects.create(order=entry,name='Figura',unit_price=10000)
        issue=CustomerIssue.objects.create(entry=entry,comment='Reporte a conservar')
        entry.image.save('test.png',ContentFile(b'owned'),save=True);image_path=Path(entry.image.path)
        message=OperationalEmail.objects.create(entry=entry,event_key='delete-test',recipient='client@example.com',subject='Test',text='',html='')
        message.attachment.save('own.pdf',ContentFile(b'pdf'),save=True);pdf_path=Path(message.attachment.path)
        path=reverse('management:delete_entry',args=[entry.pk])
        self.assertEqual(self.client.get(path).status_code,200);self.assertTrue(Entry.objects.filter(pk=entry.pk).exists())
        self.assertEqual(self.client.post(path).status_code,400)
        with self.captureOnCommitCallbacks(execute=True):response=self.client.post(path,{'confirm_delete':str(entry.pk)})
        self.assertEqual(response.status_code,302)
        self.assertFalse(Entry.objects.filter(pk=entry.pk).exists());self.assertEqual(Payment.objects.count(),0)
        self.assertEqual(OperationalEmail.objects.count(),0);self.assertEqual(QuoteItem.objects.count(),0)
        issue.refresh_from_db();self.assertIsNone(issue.entry_id)
        self.assertFalse(image_path.exists());self.assertFalse(pdf_path.exists())
        self.assertEqual(self.client.get('/gestion/').context['sales'],0)

    def test_bulk_delete_previews_then_deletes_only_commercial_selection(self):
        a=self.quote();b=self.quote(kind='sale');expense=self.quote(kind='expense')
        path=reverse('management:bulk_delete');payload={'entries':[str(a.pk),str(b.pk),str(expense.pk)]}
        self.assertContains(self.client.post(path,payload),'Revisa lo que vas a eliminar')
        self.assertEqual(Entry.objects.count(),3)
        with self.captureOnCommitCallbacks(execute=True):self.client.post(path,{**payload,'confirm_delete':'yes'})
        self.assertEqual(list(Entry.objects.values_list('pk',flat=True)),[expense.pk])
        self.assertEqual(Client().post(path,payload).status_code,302)
        normal=get_user_model().objects.create_user('notstaff');client=Client();client.force_login(normal)
        self.assertEqual(client.post(path,payload).status_code,403)
        self.assertEqual(self.client.get(path).status_code,405)

    def test_delivery_window_migration_repairs_only_actual_send_time(self):
        entry=self.quote(status='expired',quote_sent_at=timezone.now()-timedelta(days=4),quote_expires_at=timezone.now()-timedelta(days=2))
        accepted=timezone.now()-timedelta(hours=1)
        OperationalEmail.objects.create(entry=entry,event_key=f'quote:{entry.pk}:{entry.approval_nonce}',recipient=entry.customer_email,
            subject='Quote',text='',html='',status='sent',sent_at=accepted)
        failed=self.quote(status='expired',quote_expires_at=timezone.now()-timedelta(days=1))
        OperationalEmail.objects.create(entry=failed,event_key=f'quote:{failed.pk}:{failed.approval_nonce}',subject='Failed',text='',html='',status='failed')
        repair=import_module('apps.management.migrations.0016_quote_delivery_window').repair_windows
        repair(apps,None)
        entry.refresh_from_db();failed.refresh_from_db()
        self.assertEqual(entry.status,'sent');self.assertEqual(entry.quote_expires_at,accepted+timedelta(hours=48))
        self.assertEqual(failed.status,'sent');self.assertIsNone(failed.quote_expires_at)

    def test_issue_storage_failure_keeps_customer_comment(self):
        entry=self.quote();token=self.send(entry)
        with patch('apps.management.commerce.CustomerIssue.objects.create',side_effect=RuntimeError('database unavailable')):
            response=Client().post(reverse('management:customer_issue',args=[token]),{'comment':'Error al aprobar, por favor ayúdame.'})
        self.assertContains(response,'Tu información sigue aquí')
        self.assertContains(response,'Error al aprobar, por favor ayúdame.')
        self.assertEqual(CustomerIssue.objects.count(),0)

    @override_settings(ALLOWED_HOSTS=['testserver','www.villatechubate.com'])
    def test_https_native_form_without_origin_uses_same_site_referer(self):
        entry=self.quote();token=self.send(entry)
        path=reverse('management:customer_quote',args=[token])
        public=Client(enforce_csrf_checks=True)
        page=public.get(path,secure=True,HTTP_HOST='www.villatechubate.com')
        self.assertEqual(page['Referrer-Policy'],'same-origin')
        self.assertContains(page,'<meta name="referrer" content="same-origin">')
        self.assertNotContains(page,'content="no-referrer"')
        csrf=public.cookies['csrftoken'].value
        # Reproduces HTTPS + valid cookie/token + policy that removed Referer.
        rejected=public.post(path,{'accept':'yes','csrfmiddlewaretoken':csrf},secure=True,HTTP_HOST='www.villatechubate.com')
        self.assertEqual(rejected.status_code,403)
        entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
        # same-origin allows the native form to send this same-site Referer.
        with self.captureOnCommitCallbacks(execute=True):
            response=public.post(path,{'accept':'yes','csrfmiddlewaretoken':csrf},secure=True,
                HTTP_HOST='www.villatechubate.com',HTTP_REFERER='https://www.villatechubate.com'+path)
        self.assertEqual(response.status_code,302)
        entry.refresh_from_db();self.assertEqual(entry.kind,'order')

    @override_settings(ALLOWED_HOSTS=['testserver','www.villatechubate.com'])
    def test_https_issue_form_without_origin_preserves_referrer_and_sends(self):
        entry=self.quote();token=self.send(entry)
        path=reverse('management:customer_issue',args=[token])
        public=Client(enforce_csrf_checks=True)
        page=public.get(path,secure=True,HTTP_HOST='www.villatechubate.com')
        self.assertEqual(page['Referrer-Policy'],'same-origin')
        self.assertContains(page,'<meta name="referrer" content="same-origin">')
        with self.captureOnCommitCallbacks(execute=True):
            response=public.post(path,{'comment':'No puedo confirmar la cotización.',
                'csrfmiddlewaretoken':public.cookies['csrftoken'].value},secure=True,
                HTTP_HOST='www.villatechubate.com',HTTP_REFERER='https://www.villatechubate.com'+path)
        self.assertEqual(response.status_code,302)
        self.assertEqual(CustomerIssue.objects.count(),1)
        self.assertEqual(mail.outbox[-1].to,['owner@example.com'])

    @override_settings(ALLOWED_HOSTS=['testserver','www.villatechubate.com'])
    def test_https_foreign_referer_is_rejected_with_valid_token(self):
        entry=self.quote();token=self.send(entry)
        path=reverse('management:customer_quote',args=[token])
        public=Client(enforce_csrf_checks=True);public.get(path,secure=True,HTTP_HOST='www.villatechubate.com')
        response=public.post(path,{'accept':'yes','csrfmiddlewaretoken':public.cookies['csrftoken'].value},
            secure=True,HTTP_HOST='www.villatechubate.com',HTTP_REFERER='https://attacker.example/form')
        self.assertEqual(response.status_code,403)
        self.assertEqual(response['Referrer-Policy'],'same-origin')
        self.assertContains(response,'<meta name="referrer" content="same-origin">',status_code=403)
        entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
