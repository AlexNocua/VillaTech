from datetime import date
from decimal import Decimal as D
from io import BytesIO
from tempfile import TemporaryDirectory
from pathlib import Path
from PIL import Image
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.core.cache import cache
from .models import Entry,QuoteItem,Payment,ProductReview,OperationalEmail
from .cleanup import delete_commercial_entry
from .reviews import ReviewSetupForm
from apps.landing.models import Product,CategoryProduct

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',PUBLIC_SITE_URL='https://villatech.example')
class DeliveryReviewTests(TestCase):
    def setUp(self):
        cache.clear();self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.tmp.name);self.override.enable();self.addCleanup(self.override.disable)
        self.staff=get_user_model().objects.create_user('reviews_staff',is_staff=True)
        self.client.force_login(self.staff)
        self.entry=Entry.objects.create(kind='order',status='ready',title='Producto de prueba',customer='Cliente completo',customer_email='client@example.com',amount=300,paid_amount=50,estimated_delivery_date=date(2026,10,21))
    def image(self,name='photo.png'):
        data=BytesIO();Image.new('RGB',(12,12),'green').save(data,format='PNG');return SimpleUploadedFile(name,data.getvalue(),content_type='image/png')
    def deliver_due(self):
        response=self.client.post(reverse('management:update_delivery',args=[self.entry.pk]),{'status':'delivered_due','estimated_delivery_date':''})
        self.assertEqual(response.status_code,302);self.entry.refresh_from_db();return self.entry
    def invitation(self,item=None):
        self.entry.status='delivered_due';self.entry.save()
        obj=item or self.entry;obj.image.save('ref.png',self.image(),save=True);obj.final_image.save('final.png',self.image(),save=True)
        response=self.client.post(reverse('management:prepare_item_review' if item else 'management:prepare_review',args=[self.entry.pk,item.pk] if item else [self.entry.pk]))
        self.assertEqual(response.status_code,302);return ProductReview.objects.get(entry=self.entry,item=item)
    def submit(self,review,**values):
        data={'full_name':'Cliente Real','rating':4,'comment':'Me gustó mucho','consent':'on'};data.update(values)
        return Client().post(reverse('management:customer_review',args=[review.token]),data)
    def test_unpaid_delivery_keeps_paid_and_outstanding_and_ledger(self):
        self.deliver_due();self.assertEqual((self.entry.kind,self.entry.status,self.entry.paid_amount,self.entry.outstanding,self.entry.delivery_settled_amount),('order','delivered_due',D('50'),D('250'),0))
        self.assertFalse(Payment.objects.exists())
        page=self.client.get(reverse('management:dashboard'));self.assertEqual(page.context['sales'],300);self.assertEqual(page.context['collected'],50);self.assertEqual(page.context['delivered_due_total'],250)
        self.assertFalse(__import__('apps.management.workflow',fromlist=['active_orders']).active_orders().filter(pk=self.entry.pk).exists())
    def test_unpaid_highlight_button_and_filters_and_calendar(self):
        self.deliver_due()
        for url in [reverse('management:orders'),reverse('management:workflow'),reverse('management:workflow_detail',args=[self.entry.pk])]:
            response=self.client.get(url);self.assertContains(response,'Registrar pago y cerrar');self.assertContains(response,'Entregado')
        response=self.client.get(reverse('management:workflow'),{'status':'delivered_due','payment':'pending'});self.assertEqual(response.context['page'].paginator.count,1)
        response=self.client.get(reverse('management:calendar'),{'date':'2026-10-21','basis':'delivery','status':'delivered_due'});self.assertEqual(response.context['total'],1)
    def test_one_click_payment_is_idempotent(self):
        self.deliver_due();url=reverse('management:settle_delivered',args=[self.entry.pk])
        self.client.post(url);self.client.post(url);self.entry.refresh_from_db()
        self.assertEqual((self.entry.kind,self.entry.status,self.entry.paid_amount,self.entry.outstanding),('sale','sold',D('300'),0))
        self.assertEqual(Payment.objects.count(),1);self.assertEqual(Payment.objects.get().amount,250)
        self.assertEqual(self.entry.delivery_settled_amount,0)
        self.assertEqual(OperationalEmail.objects.filter(entry=self.entry,subject__contains='Pago recibido').count(),1)
    def test_partial_then_final_payment_closes_delivered_order(self):
        self.deliver_due();url=reverse('management:record_payment',args=[self.entry.pk])
        self.client.post(url,{'payment':20});self.entry.refresh_from_db();self.assertEqual(self.entry.status,'delivered_due');self.assertEqual(self.entry.outstanding,230)
        self.client.post(url,{'payment':230});self.entry.refresh_from_db();self.assertEqual(self.entry.kind,'sale');self.assertEqual(self.entry.paid_amount,300);self.assertEqual(Payment.objects.count(),2)
    def test_closed_production_cannot_reopen_and_get_does_not_collect(self):
        self.deliver_due();self.client.post(reverse('management:update_delivery',args=[self.entry.pk]),{'status':'printing'})
        self.entry.refresh_from_db();self.assertEqual(self.entry.status,'delivered_due')
        self.assertEqual(self.client.get(reverse('management:settle_delivered',args=[self.entry.pk])).status_code,405)
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(self.client.get(reverse('management:workflow_edit',args=[self.entry.pk])).status_code,302)
    def test_original_paid_delivery_keeps_previous_behavior(self):
        self.client.post(reverse('management:update_delivery',args=[self.entry.pk]),{'status':'delivered'})
        self.entry.refresh_from_db();self.assertEqual((self.entry.kind,self.entry.paid_amount,self.entry.delivery_settled_amount),('sale',300,250))
    def test_paid_order_marked_due_closes_without_new_receipt(self):
        self.entry.paid_amount=300;self.entry.save();self.deliver_due();self.assertEqual(self.entry.kind,'sale');self.assertFalse(Payment.objects.exists())
    def test_settle_requires_staff_and_delivered_state(self):
        url=reverse('management:settle_delivered',args=[self.entry.pk]);self.assertEqual(Client().post(url).status_code,302)
        self.client.post(url);self.assertFalse(Payment.objects.exists());self.entry.refresh_from_db();self.assertEqual(self.entry.status,'ready')
    def test_prepare_only_after_delivery_and_repeat_reuses_link(self):
        self.client.post(reverse('management:prepare_review',args=[self.entry.pk]));self.assertFalse(ProductReview.objects.exists())
        review=self.invitation();old=review.token
        self.client.post(reverse('management:prepare_review',args=[self.entry.pk]));review.refresh_from_db()
        self.assertEqual(ProductReview.objects.count(),1);self.assertEqual(review.token,old)
        self.assertNotEqual(review.reference_image.name,self.entry.image.name)
    def test_per_product_images_and_separate_invitations(self):
        a=QuoteItem.objects.create(order=self.entry,name='Pieza A',quantity=2,unit_price=50)
        b=QuoteItem.objects.create(order=self.entry,name='Pieza B',quantity=1,unit_price=200)
        ra=self.invitation(a);rb=self.invitation(b);self.assertNotEqual(ra.token,rb.token);self.assertEqual((ra.product_title,ra.quantity),('Pieza A',2))
        response=self.client.get(reverse('management:workflow_detail',args=[self.entry.pk]));self.assertContains(response,'Pieza A');self.assertContains(response,'Pieza B')
    def test_upload_images_and_staff_only_access(self):
        response=self.client.post(reverse('management:order_photos',args=[self.entry.pk]),{'image':self.image('ref.png'),'final_image':self.image('finished.png')})
        self.assertEqual(response.status_code,302);self.entry.refresh_from_db();self.assertTrue(self.entry.final_image)
        url=reverse('management:order_photo',args=[self.entry.pk,'final']);self.assertEqual(Client().get(url).status_code,302)
        response=self.client.get(url);self.assertEqual(response.status_code,200);response.close()
    def test_invalid_uploaded_image_rejected(self):
        response=self.client.post(reverse('management:order_photos',args=[self.entry.pk]),{'final_image':SimpleUploadedFile('fake.png',b'not an image',content_type='image/png')})
        self.assertEqual(response.status_code,200);self.assertTrue(response.context['form'].errors);self.entry.refresh_from_db();self.assertFalse(self.entry.final_image)
    def test_missing_images_prevent_live_form(self):
        self.entry.status='delivered_due';self.entry.save();self.client.post(reverse('management:prepare_review',args=[self.entry.pk]));review=ProductReview.objects.get()
        self.assertEqual(Client().get(reverse('management:customer_review',args=[review.token])).status_code,404)
        page=self.client.get(reverse('management:review_edit',args=[review.pk]));self.assertFalse(page.context['share_url'])
    def test_customer_only_controls_name_rating_and_optional_comment(self):
        review=self.invitation();response=self.submit(review,comment='',product_title='Changed',is_published='on',quantity=999)
        self.assertEqual(response.status_code,302);review.refresh_from_db();self.assertEqual((review.rating,review.comment,review.product_title,review.quantity,review.is_published),(4,'','Producto de prueba',1,False));self.assertTrue(review.submitted_at)
        self.submit(review,rating=1,full_name='Changed');review.refresh_from_db();self.assertEqual((review.rating,review.full_name),(4,'Cliente Real'))
    def test_invalid_rating_retains_form_information(self):
        review=self.invitation();response=self.submit(review,rating=6,comment='Datos conservados')
        self.assertEqual(response.status_code,400);self.assertContains(response,'Datos conservados',status_code=400);review.refresh_from_db();self.assertIsNone(review.submitted_at)
    def test_consent_required(self):
        review=self.invitation();response=self.submit(review,consent='');self.assertEqual(response.status_code,400);review.refresh_from_db();self.assertIsNone(review.submitted_at)
    def test_opinion_section_hidden_until_publish_and_hides_again(self):
        self.assertNotContains(Client().get('/'),'id="opiniones"')
        review=self.invitation();self.submit(review,comment='Seguro <script>bad()</script>')
        self.assertNotContains(Client().get('/'),'id="opiniones"')
        self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'publish'})
        response=Client().get('/');self.assertContains(response,'id="opiniones"');self.assertContains(response,'Cliente Real');self.assertContains(response,'&lt;script&gt;bad()&lt;/script&gt;');self.assertNotContains(response,'<script>bad()</script>')
        self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'hide'});self.assertNotContains(Client().get('/'),'id="opiniones"')
    def test_image_access_requires_link_or_published_consent(self):
        review=self.invitation();url=reverse('management:review_image',args=[review.pk,'final'])
        self.assertEqual(Client().get(url).status_code,404)
        response=Client().get(url,{'token':str(review.token)});self.assertEqual(response.status_code,200);response.close()
        self.submit(review);self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'publish'})
        response=Client().get(url);self.assertEqual(response.status_code,200);response.close()
        self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'hide'});self.assertEqual(Client().get(url).status_code,404)
    def test_renew_and_revoke_invalidate_old_token(self):
        review=self.invitation();old=reverse('management:customer_review',args=[review.token]);self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'renew'});review.refresh_from_db()
        self.assertEqual(Client().get(old).status_code,404)
        self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'revoke'});self.assertEqual(Client().get(reverse('management:customer_review',args=[review.token])).status_code,404)
    def test_only_staff_can_publish_and_no_publish_without_response(self):
        review=self.invitation();url=reverse('management:review_action',args=[review.pk]);self.assertEqual(Client().post(url,{'action':'publish'}).status_code,302)
        self.client.post(url,{'action':'publish'});review.refresh_from_db();self.assertFalse(review.is_published)
    def test_staff_title_can_be_manual_or_catalogue(self):
        review=self.invitation();cat=CategoryProduct.objects.create(category_name='3D');product=Product.objects.create(name='Producto del catálogo',price=1,mtm_category=cat)
        form=ReviewSetupForm({'product':product.pk,'product_title':'','is_active':'on'},instance=review);self.assertTrue(form.is_valid(),form.errors);form.save();review.refresh_from_db();self.assertEqual(review.product_title,product.name)
        self.assertEqual(self.client.get(reverse('management:review_edit',args=[review.pk])).status_code,200)
    def test_csrf_enforced_and_https_post_with_cookie_works(self):
        review=self.invitation();url=reverse('management:customer_review',args=[review.token]);browser=Client(enforce_csrf_checks=True)
        page=browser.get(url,secure=True);self.assertEqual(page['Referrer-Policy'],'same-origin')
        data={'full_name':'Cliente Seguro','rating':'5','comment':'','consent':'on'}
        self.assertEqual(browser.post(url,data,secure=True).status_code,403)
        token=browser.cookies['csrftoken'].value
        self.assertEqual(browser.post(url,data,secure=True,HTTP_X_CSRFTOKEN=token,HTTP_REFERER='https://testserver'+url).status_code,302)
    def test_delete_entry_cleans_review_images_and_unpublishes(self):
        review=self.invitation();self.submit(review);self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'publish'})
        owned=[Path(review.reference_image.path),Path(review.final_image.path),Path(self.entry.final_image.path)]
        with self.captureOnCommitCallbacks(execute=True):delete_commercial_entry(self.entry)
        self.assertFalse(ProductReview.objects.exists());self.assertTrue(all(not path.exists() for path in owned));self.assertNotContains(Client().get('/'),'id="opiniones"')
    def test_missing_original_can_be_completed_manually_in_invitation(self):
        self.entry.status='delivered_due';self.entry.image='private/missing.png';self.entry.save()
        response=self.client.post(reverse('management:prepare_review',args=[self.entry.pk]))
        self.assertEqual(response.status_code,302);review=ProductReview.objects.get();self.assertFalse(review.reference_image)
        response=self.client.get(reverse('management:review_edit',args=[review.pk]));self.assertEqual(response.status_code,200);self.assertFalse(response.context['share_url'])
