from datetime import date, timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from .models import Entry, OperationalEmail
from .workflow import estimate_delivery, approve_order, dispatch_emails, queue_daily_digest

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_NOTIFICATION_EMAIL='owner@example.com',DEFAULT_FROM_EMAIL='VillaTech <sender@example.com>',
    PUBLIC_SITE_URL='https://villatech.example')
class OrderWorkflowTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user('operator',is_staff=True)
        self.client.force_login(self.staff)
    def order(self, **extra):
        defaults = dict(kind='order',title='Pieza <script>mala</script>',amount=100000,customer='Cliente',
                        customer_email='customer@example.com',created_by=self.staff)
        defaults.update(extra)
        return Entry.objects.create(**defaults)
    def test_estimation_skips_weekend_and_respects_queue(self):
        first = self.order(print_hours=0)
        self.assertEqual(estimate_delivery(first,date(2026,10,9)),date(2026,10,14))
        first.estimated_delivery_date=date(2026,10,16);first.save()
        second=self.order(print_hours=8)
        self.assertEqual(estimate_delivery(second,date(2026,10,9)),date(2026,10,19))
    def test_approval_snapshot_logo_and_no_duplicate(self):
        order=self.order()
        msg=approve_order(order)
        self.assertIsNotNone(order.approved_at)
        self.assertIsNotNone(order.estimated_delivery_date)
        self.assertEqual(dispatch_emails(msg.pk),1)
        self.assertEqual(dispatch_emails(msg.pk),0)
        self.assertIsNone(approve_order(order))
        self.assertEqual(OperationalEmail.objects.count(),1)
        sent=mail.outbox[0]
        self.assertIn(order.estimated_delivery_date.strftime('%d/%m/%Y'),sent.body)
        self.assertNotIn('/gestion/',sent.body)
        self.assertNotIn('<script>',sent.alternatives[0].content)
        self.assertIn('cid:villatech-logo',sent.alternatives[0].content)
        self.assertEqual(sent.attachments[0]['Content-ID'],'<villatech-logo>')
        self.assertIn('image/png',sent.message().as_string())
    def test_approval_without_email_preserves_order_and_balance(self):
        order=self.order(customer_email='')
        self.assertIsNone(approve_order(order))
        self.assertEqual(OperationalEmail.objects.count(),0)
        self.assertEqual(self.client.get('/gestion/').context['sales'],100000)
        self.assertEqual(order.outstanding,100000)
    def test_confirmation_uses_staff_date_and_repeated_post_is_blocked(self):
        quote=self.order(kind='quote',status='quoted')
        day=timezone.localdate()+timedelta(days=5)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f'/gestion/registro/{quote.pk}/convertir/order/',{'estimated_delivery_date':day.isoformat()})
        quote.refresh_from_db()
        self.assertEqual(quote.estimated_delivery_date,day)
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(self.client.post(f'/gestion/registro/{quote.pk}/convertir/order/').status_code,400)
        self.assertEqual(Entry.objects.count(),1)
    def test_invalid_confirmation_keeps_quote(self):
        quote=self.order(kind='quote',status='quoted')
        self.client.post(f'/gestion/registro/{quote.pk}/convertir/order/',{'estimated_delivery_date':'ayer'})
        quote.refresh_from_db();self.assertEqual(quote.kind,'quote')
        self.assertEqual(OperationalEmail.objects.count(),0)
    def test_status_update_delivery_and_archive_keep_receivable(self):
        order=self.order()
        approve_order(order);dispatch_emails()
        path=f'/gestion/registro/{order.pk}/entrega/'
        day=timezone.localdate()+timedelta(days=6)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(path,{'status':'printing','estimated_delivery_date':day.isoformat()})
        self.assertEqual(len(mail.outbox),2)
        self.client.post(path,{'status':'printing','estimated_delivery_date':day.isoformat()})
        self.assertEqual(OperationalEmail.objects.count(),2)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(path,{'status':'delivered','estimated_delivery_date':day.isoformat()})
        self.client.post(f'/gestion/registro/{order.pk}/convertir/sale/')
        order.refresh_from_db();self.assertEqual(order.kind,'sale')
        self.assertEqual(order.outstanding,100000)
        self.assertEqual(self.client.get('/gestion/').context['pending'],0)
    def test_cannot_cancel_paid_order_or_archive_before_delivery(self):
        order=self.order(paid_amount=1000)
        self.client.post(f'/gestion/registro/{order.pk}/entrega/',{'status':'cancelled'})
        self.client.post(f'/gestion/registro/{order.pk}/convertir/sale/')
        order.refresh_from_db();self.assertEqual((order.kind,order.status),('order','pending'))
    def test_failure_is_recorded_and_retry_only_resends_failed(self):
        msg=approve_order(self.order())
        with patch('django.core.mail.message.EmailMultiAlternatives.send',side_effect=OSError(101,'private text')):
            self.assertEqual(dispatch_emails(msg.pk),0)
        msg.refresh_from_db();self.assertEqual(msg.status,'failed')
        self.assertNotIn('private text',msg.last_error)
        self.assertEqual(dispatch_emails(msg.pk),1)
        self.assertEqual(dispatch_emails(msg.pk),0)
    def test_daily_digest_counts_and_unique_day(self):
        today=timezone.localdate()
        self.order(estimated_delivery_date=today-timedelta(days=1))
        self.order(estimated_delivery_date=today)
        self.order(estimated_delivery_date=today+timedelta(days=3))
        self.order()
        self.order(status='delivered',estimated_delivery_date=today)
        self.order(status='cancelled',estimated_delivery_date=today)
        message=queue_daily_digest()
        self.assertIn('Pendientes: 4',message.text)
        self.assertIn('Vencidos: 1',message.text)
        self.assertIn('Sin fecha: 1',message.text)
        call_command('send_order_alerts')
        call_command('send_order_alerts')
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,['owner@example.com'])
        self.assertEqual(OperationalEmail.objects.count(),1)
        response=self.client.get('/gestion/pedidos/?due=overdue')
        self.assertEqual(response.context['page'].paginator.count,1)
    def test_no_pending_no_digest_and_staff_screens(self):
        self.assertIsNone(queue_daily_digest())
        for path in ['/gestion/gastos/','/gestion/variantes/','/gestion/productos/','/gestion/pedidos/','/gestion/ventas/']:
            self.assertEqual(self.client.get(path).status_code,200)
