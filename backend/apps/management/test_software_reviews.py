from io import BytesIO
from tempfile import TemporaryDirectory
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError,transaction
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from .models import DevelopmentProject,ProjectScreenshot,ProductReview,Entry
from .reviews import ReviewSetupForm

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',PUBLIC_SITE_URL='https://villatech.example')
class SoftwareReviewTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.media=override_settings(MEDIA_ROOT=self.tmp.name);self.media.enable();self.addCleanup(self.media.disable)
        self.staff=get_user_model().objects.create_user('software_reviews',is_staff=True);self.client.force_login(self.staff)
        self.project=DevelopmentProject.objects.create(name='Aplicación del cliente',customer='Cliente software',description='Información interna NO PUBLICAR',project_type='software',status='delivered',created_by=self.staff)
        self.prepare=reverse('management:prepare_software_review',args=[self.project.pk])
    def image(self):
        data=BytesIO();Image.new('RGB',(10,10),'green').save(data,format='PNG');return SimpleUploadedFile('screen.png',data.getvalue(),content_type='image/png')
    def invitation(self):
        ProjectScreenshot.objects.create(project=self.project,image=self.image())
        self.client.post(self.prepare);review=ProductReview.objects.get(development=self.project)
        review.reference_image.save('reference.png',self.image(),save=True);review.public_summary='Aplicación para gestionar inventario';review.save()
        return review
    def test_finalized_projects_have_reusable_opinion_links(self):
        review=self.invitation();self.client.post(self.prepare)
        self.assertEqual(ProductReview.objects.count(),1);self.assertIsNone(review.entry_id);self.assertTrue(review.final_image);self.assertEqual(review.review_type,'software')
        self.assertContains(self.client.get(reverse('management:development')),'Preparar opinión del desarrollo')
        self.assertContains(self.client.get(reverse('management:review_edit',args=[review.pk])),'Abrir desarrollo')
    def test_active_project_cannot_receive_reviews_yet(self):
        self.project.status='active';self.project.save();self.client.post(self.prepare);self.assertFalse(ProductReview.objects.exists())
    def test_form_shows_public_summary_and_captures_without_private_notes(self):
        review=self.invitation();url=reverse('management:customer_review',args=[review.token]);response=Client().get(url)
        self.assertContains(response,'¿Qué te pareció tu proyecto?');self.assertContains(response,'Aplicación para gestionar inventario');self.assertNotContains(response,'Información interna NO PUBLICAR')
        photo=reverse('management:review_image',args=[review.pk,'final']);self.assertEqual(Client().get(photo).status_code,404)
    def test_software_submission_and_public_category_use_real_rating(self):
        review=self.invitation();url=reverse('management:customer_review',args=[review.token])
        response=Client().post(url,{'full_name':'Cliente de software','rating':'3','comment':'Buena aplicación','consent':'on','review_type':'product'})
        self.assertEqual(response.status_code,302);review.refresh_from_db();self.assertEqual(review.review_type,'software');self.assertEqual(review.rating,3);self.assertFalse(review.is_published)
        self.client.post(reverse('management:review_action',args=[review.pk]),{'action':'publish'})
        response=Client().get('/');self.assertContains(response,'data-review-kind="software"');self.assertContains(response,'Desarrollo verificado');self.assertContains(response,'3 de 5 estrellas');self.assertContains(response,'type="module" src="/static/landing/js/reviews.js?v=19"')
    def test_staff_filter_separates_software_from_product_opinions(self):
        review=self.invitation();order=Entry.objects.create(kind='sale',title='Figura',amount=1)
        ProductReview.objects.create(entry=order,subject_key='entry',product_title='Figura')
        response=self.client.get(reverse('management:reviews'),{'type':'software'});self.assertEqual([item.pk for item in response.context['page']],[review.pk])
    def test_origin_must_be_project_or_order_but_not_both(self):
        order=Entry.objects.create(kind='sale',title='Figura',amount=1)
        with self.assertRaises(IntegrityError),transaction.atomic():ProductReview.objects.create(subject_key='none',product_title='No origin')
        with self.assertRaises(IntegrityError),transaction.atomic():ProductReview.objects.create(entry=order,development=self.project,subject_key='both',product_title='Dual origin')
    def test_preparation_requires_staff_and_post(self):
        self.assertEqual(Client().post(self.prepare).status_code,302);self.assertEqual(self.client.get(self.prepare).status_code,405);self.assertFalse(ProductReview.objects.exists())
    def test_catalogue_order_can_be_classified_as_software_manually(self):
        order=Entry.objects.create(kind='sale',title='Sitio web',amount=1)
        review=ProductReview.objects.create(entry=order,subject_key='entry',product_title='Sitio web')
        review.reference_image.save('reference.png',self.image(),save=True);review.final_image.save('finished.png',self.image(),save=True)
        form=ReviewSetupForm({'review_type':'software','product_title':'Página corporativa','public_summary':'Descripción pública','is_active':'on'},instance=review)
        self.assertTrue(form.is_valid(),form.errors);form.save();review.refresh_from_db();self.assertEqual(review.review_type,'software')
    def test_no_opinions_still_hides_entire_section_and_scripts(self):
        response=Client().get('/');self.assertNotContains(response,'id="opiniones"');self.assertNotContains(response,'landing/js/reviews.js')

    def test_public_listing_keeps_all_published_opinions_beyond_twenty_four(self):
        from django.utils import timezone
        review=self.invitation()
        for index in range(28):
            ProductReview.objects.create(development=self.project,subject_key='published-%s'%index,
                product_title='Proyecto %s'%index,review_type='software',full_name='Cliente',
                rating=5,consent=True,is_published=True,submitted_at=timezone.now(),
                reference_image=review.reference_image.name,final_image=review.final_image.name)
        response=Client().get('/')
        self.assertEqual(len(response.context['customer_reviews']),28)
        self.assertContains(response,'data-review-more')
        self.assertContains(response,'aria-controls="review-grid"')
        self.assertContains(response,'landing/js/review-list.js?v=19')
