from datetime import timedelta
from decimal import Decimal
import tempfile
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from .models import Entry,QuoteItem,OperationalEmail,EntryActivity
from .quotations import approval_token,send_quotation,confirm_quotation,expire_quotes,renew_quotation,recalculate
from .workflow import dispatch_emails

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',CONTACT_NOTIFICATION_EMAIL='owner@example.com',
 DEFAULT_FROM_EMAIL='VillaTech <sender@example.com>',PUBLIC_SITE_URL='https://villatech.example')
class CommerceTests(TestCase):
 def setUp(self):
  self.staff=get_user_model().objects.create_user('commercial',is_staff=True)
  self.client.force_login(self.staff)
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.override=override_settings(MEDIA_ROOT=self.temp.name);self.override.enable();self.addCleanup(self.override.disable)
 def quote(self,**kwargs):
  data=dict(kind='quote',status='quoted',title='Pieza segura <script>x</script>',customer='Alex',
    customer_email='client@example.com',amount=10000,quantity=2,unit_price=5000,unit_filament_g=25,unit_print_hours=1,created_by=self.staff)
  data.update(kwargs);return Entry.objects.create(**data)
 def send(self,entry):
  with self.captureOnCommitCallbacks(execute=True):
   self.client.post(reverse('management:send_quotation',args=[entry.pk]))
  entry.refresh_from_db();return approval_token(entry)
 def test_units_and_item_totals(self):
  entry=self.quote();recalculate(entry)
  self.assertEqual((entry.amount,entry.filament_g,entry.print_hours),(10000,50,2))
  QuoteItem.objects.create(order=entry,name='Figura',quantity=2,unit_price=8000,unit_filament_g=35,unit_print_hours=3)
  QuoteItem.objects.create(order=entry,name='Base',quantity=3,unit_price=2000,unit_filament_g=5,unit_print_hours=Decimal('.5'))
  recalculate(entry)
  self.assertEqual((entry.amount,entry.filament_g,entry.print_hours,entry.total_units),(22000,85,Decimal('7.5'),5))
 def test_send_pdf_and_repeated_send_does_not_duplicate(self):
  entry=self.quote();self.send(entry);deadline=entry.quote_expires_at
  self.assertEqual(entry.status,'sent');self.assertEqual(len(mail.outbox),1)
  self.assertTrue(OperationalEmail.objects.get().attachment)
  self.assertIn('application/pdf',mail.outbox[0].message().as_string())
  self.assertIn('confirmar-cotizacion/',mail.outbox[0].body)
  self.assertNotIn('<script>',mail.outbox[0].alternatives[0].content)
  self.send(entry);self.assertEqual(OperationalEmail.objects.count(),1)
  entry.refresh_from_db();self.assertEqual(deadline,entry.quote_expires_at)
 def test_get_is_readonly_and_post_confirms_once(self):
  entry=self.quote();token=self.send(entry);public=Client();url=reverse('management:customer_quote',args=[token])
  self.assertEqual(public.get(url).status_code,200)
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
  with self.captureOnCommitCallbacks(execute=True):self.assertEqual(public.post(url,{'accept':'yes'}).status_code,302)
  entry.refresh_from_db();self.assertEqual((entry.kind,entry.status,entry.approval_channel),('order','pending','email'))
  self.assertIsNotNone(entry.estimated_delivery_date);self.assertEqual(entry.paid_amount,0)
  public.post(url,{'accept':'yes'})
  self.assertEqual(Entry.objects.count(),1);self.assertEqual(OperationalEmail.objects.count(),2)
  self.assertEqual(self.client.get('/gestion/').context['sales'],10000)
 def test_public_csrf_required_and_tampered_token_rejected(self):
  entry=self.quote();token=self.send(entry);url=reverse('management:customer_quote',args=[token])
  self.assertEqual(Client(enforce_csrf_checks=True).post(url,{'accept':'yes'}).status_code,403)
  response=Client().get(reverse('management:customer_quote',args=[token+'x']))
  self.assertContains(response,'Solicita una nueva versión')
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
 def test_expiry_blocks_manual_and_public_approval(self):
  entry=self.quote();token=self.send(entry)
  Entry.objects.filter(pk=entry.pk).update(quote_expires_at=timezone.now()-timedelta(seconds=1))
  call_command('process_quote_expiry');entry.refresh_from_db();self.assertEqual(entry.status,'expired')
  self.assertEqual(expire_quotes(),0)
  with self.assertRaises(ValidationError):confirm_quotation(entry,'message')
  Client().post(reverse('management:customer_quote',args=[token]),{'accept':'yes'})
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
  self.assertEqual(self.client.get('/gestion/').context['sales'],0)
 def test_renew_invalidates_old_link_and_reissue_is_new_snapshot(self):
  entry=self.quote();token=self.send(entry);renew_quotation(entry,self.staff)
  self.assertContains(Client().get(reverse('management:customer_quote',args=[token])),'Solicita una nueva versión')
  self.send(entry);self.assertEqual(OperationalEmail.objects.count(),2)
 def test_manual_message_approval_requires_evidence(self):
  entry=self.quote();path=reverse('management:confirm_quotation',args=[entry.pk])
  self.assertEqual(self.client.post(path,{'channel':'message'}).status_code,400)
  with self.captureOnCommitCallbacks(execute=True):self.client.post(path,{'channel':'message','note':'WhatsApp 09 octubre'})
  entry.refresh_from_db();self.assertEqual(entry.approval_note,'WhatsApp 09 octubre')
  self.assertEqual(entry.kind,'order');self.assertEqual(len(mail.outbox),1)
 def test_failed_send_retained_and_expired_retry_suppressed(self):
  entry=self.quote()
  with patch('django.core.mail.message.EmailMultiAlternatives.send',side_effect=OSError('offline')):self.send(entry)
  message=OperationalEmail.objects.get();self.assertEqual(message.status,'failed')
  Entry.objects.filter(pk=entry.pk).update(quote_expires_at=timezone.now()-timedelta(seconds=1))
  self.assertEqual(dispatch_emails(message.pk),0)
  message.refresh_from_db();self.assertEqual(message.status,'skipped')
 def test_edit_prepares_new_version_and_simple_totals(self):
  entry=self.quote();token=self.send(entry)
  payload={'title':entry.title,'customer':'Alex','customer_email':'client@example.com','quantity':2,'unit_price':7000,
    'unit_filament_g':30,'unit_print_hours':2,'logo_theme':'light','items-TOTAL_FORMS':0,'items-INITIAL_FORMS':0,
    'items-MIN_NUM_FORMS':0,'items-MAX_NUM_FORMS':30}
  response=self.client.post(reverse('management:workflow_edit',args=[entry.pk]),payload)
  self.assertEqual(response.status_code,302)
  entry.refresh_from_db();self.assertEqual((entry.status,entry.amount,entry.filament_g),('quoted',14000,60))
  self.assertContains(Client().get(reverse('management:customer_quote',args=[token])),'Solicita una nueva versión')
 def test_state_emails_and_payments_after_ready(self):
  entry=self.quote();confirm_quotation(entry,'internal');entry.refresh_from_db()
  for status in ('printing','ready','delivered'):
   with self.captureOnCommitCallbacks(execute=True):self.client.post(f'/gestion/registro/{entry.pk}/entrega/',{'status':status})
  headings=list(entry.emails.values_list('subject',flat=True))
  self.assertTrue(any('elaboración' in h for h in headings));self.assertTrue(any('terminado' in h for h in headings))
  self.client.post(f'/gestion/registro/{entry.pk}/abono/',{'payment':'4000'})
  entry.refresh_from_db();self.assertEqual(entry.outstanding,6000)
 def test_workflow_screens_and_permissions(self):
  entry=self.quote()
  for url in [reverse('management:workflow'),reverse('management:workflow_create'),reverse('management:workflow_detail',args=[entry.pk])]:
   self.assertEqual(self.client.get(url).status_code,200)
  self.assertEqual(Client().post(reverse('management:send_quotation',args=[entry.pk])).status_code,302)
 def test_missing_acceptance_keeps_customer_form(self):
  entry=self.quote();token=self.send(entry)
  response=Client().post(reverse('management:customer_quote',args=[token]),{})
  self.assertContains(response,'Marca la aceptación',status_code=400)
  self.assertContains(response,'Confirmar mi pedido',status_code=400)
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
 def test_edit_cannot_erase_payment_balance(self):
  entry=self.quote();confirm_quotation(entry,'internal');entry.refresh_from_db()
  self.client.post(f'/gestion/registro/{entry.pk}/abono/',{'payment':5000})
  payload={'title':'Cambio inválido','quantity':2,'unit_price':1000,'unit_filament_g':30,'unit_print_hours':2,
   'logo_theme':'light','items-TOTAL_FORMS':0,'items-INITIAL_FORMS':0,'items-MIN_NUM_FORMS':0,'items-MAX_NUM_FORMS':30}
  response=self.client.post(reverse('management:workflow_edit',args=[entry.pk]),payload)
  self.assertContains(response,'El total no puede ser menor')
  entry.refresh_from_db();self.assertEqual((entry.amount,entry.paid_amount),(10000,5000))
 def test_approval_after_deadline_is_rejected_before_scheduler(self):
  entry=self.quote();self.send(entry)
  entry.quote_expires_at=timezone.now()-timedelta(microseconds=1);entry.save()
  with self.assertRaises(ValidationError):confirm_quotation(entry,'message')
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
 def test_secure_public_form_confirms_with_real_csrf_and_proxy(self):
  import re
  entry=self.quote();token=self.send(entry);url=reverse('management:customer_quote',args=[token])
  public=Client(enforce_csrf_checks=True)
  with override_settings(ALLOWED_HOSTS=['www.villatechubate.com','internal.example'],
       CSRF_TRUSTED_ORIGINS=['https://www.villatechubate.com'],CSRF_COOKIE_SECURE=True,
       SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')):
   response=public.get(url,HTTP_HOST='internal.example',HTTP_X_FORWARDED_PROTO='https')
   self.assertIn('csrftoken',response.cookies)
   self.assertTrue(response.cookies['csrftoken']['secure'])
   self.assertIn('no-store',response['Cache-Control'])
   csrf=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',response.content.decode()).group(1)
   response=public.post(url,{'accept':'yes','csrfmiddlewaretoken':csrf},HTTP_HOST='internal.example',
       HTTP_X_FORWARDED_PROTO='https',HTTP_ORIGIN='https://www.villatechubate.com')
   self.assertEqual(response.status_code,302)
   self.assertEqual(response['Referrer-Policy'],'no-referrer')
   entry.refresh_from_db();self.assertEqual(entry.kind,'order');self.assertEqual(entry.paid_amount,0)
   receipt=public.get(url,HTTP_HOST='www.villatechubate.com',secure=True)
   self.assertContains(receipt,'Tu pedido está confirmado');self.assertContains(receipt,'Saldo pendiente')
   self.assertEqual(receipt['X-Robots-Tag'],'noindex, nofollow')
 def test_csrf_recovery_is_branded_and_never_approves(self):
  entry=self.quote();token=self.send(entry);url=reverse('management:customer_quote',args=[token])
  public=Client(enforce_csrf_checks=True)
  response=public.post(url,{'accept':'yes'})
  self.assertContains(response,'Actualiza tu confirmación',status_code=403)
  self.assertContains(response,'Volver a revisar mi cotización',status_code=403)
  self.assertNotContains(response,'csrfmiddlewaretoken',status_code=403)
  self.assertIn('no-store',response['Cache-Control'])
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
  self.assertEqual(public.get(url).status_code,200)
 def test_untrusted_origin_is_still_rejected(self):
  entry=self.quote();token=self.send(entry);url=reverse('management:customer_quote',args=[token])
  public=Client(enforce_csrf_checks=True);public.get(url)
  with override_settings(CSRF_TRUSTED_ORIGINS=['https://www.villatechubate.com']):
   response=public.post(url,{'accept':'yes','csrfmiddlewaretoken':public.cookies['csrftoken'].value},HTTP_ORIGIN='https://attacker.example')
  self.assertEqual(response.status_code,403)
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
 def test_confirmation_disallows_other_methods(self):
  entry=self.quote();token=self.send(entry)
  response=Client().put(reverse('management:customer_quote',args=[token]))
  self.assertEqual(response.status_code,405)

 def test_stale_csrf_recovers_then_allows_explicit_confirmation(self):
  entry=self.quote();token=self.send(entry);url=reverse('management:customer_quote',args=[token])
  public=Client(enforce_csrf_checks=True);public.get(url)
  stale=public.cookies['csrftoken'].value
  from django.middleware.csrf import _get_new_csrf_string
  public.cookies['csrftoken']=_get_new_csrf_string()
  response=public.post(url,{'accept':'yes','csrfmiddlewaretoken':stale})
  self.assertEqual(response.status_code,403)
  entry.refresh_from_db();self.assertEqual(entry.kind,'quote')
  public.get(url)
  response=public.post(url,{'accept':'yes','csrfmiddlewaretoken':public.cookies['csrftoken'].value})
  self.assertEqual(response.status_code,302)
  entry.refresh_from_db();self.assertEqual(entry.kind,'order')
