from decimal import Decimal as D
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from apps.landing.models import Product, CategoryProduct, Contact, ProductVariant
from apps.landing.catalog_data import quote_text
from .models import Entry
from .forms import WorkflowForm, QuoteItemForm, ProductForm

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CatalogFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.category=CategoryProduct.objects.create(category_name='Figuras')
        self.product=Product.objects.create(name='Figura especial',description='Descripción completa. '*80,mtm_category=self.category,price=12000,unit_filament_g=25,unit_print_hours=D('1.5'),is_public=True)
        self.staff=get_user_model().objects.create_user('catalog_staff',is_staff=True)
    def login(self):self.client.force_login(self.staff)
    def test_public_detail_and_prefilled_request(self):
        response=self.client.get(reverse('landing:product_detail',args=[self.product.pk]))
        self.assertContains(response,self.product.description)
        response=self.client.get('/',{'product':self.product.pk})
        self.assertEqual(response.context['contact_form'].initial['message'],quote_text(self.product))
        self.assertEqual(response.context['contact_form'].initial['reference_product'],self.product.pk)
    def test_public_post_keeps_product_category_and_long_description(self):
        response=self.client.post('/submit',{'name':'Cliente','phone':'3204504722','email':'client@example.com','service':'impresion-3d','message':quote_text(self.product),'privacy_consent':'accepted','reference_product':self.product.pk,'unit_price':'1','product_category':'999'},HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,200)
        entry=Entry.objects.get();self.assertEqual(entry.reference_product,self.product)
        self.assertEqual(entry.product_category,self.category);self.assertEqual(entry.unit_price,D('12000'))
        self.assertEqual(entry.description,quote_text(self.product).strip());self.assertEqual(Contact.objects.get().message,entry.description)
    def test_private_product_cannot_be_requested_or_viewed(self):
        self.product.is_public=False;self.product.save()
        self.assertEqual(self.client.get(reverse('landing:product_detail',args=[self.product.pk])).status_code,404)
        response=self.client.post('/submit',{'name':'Cliente','phone':'3204504722','email':'client@example.com','service':'impresion-3d','message':'Quiero este producto','privacy_consent':'accepted','reference_product':self.product.pk},HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,400);self.assertFalse(Entry.objects.exists())
    def test_inactive_category_hides_product(self):
        self.category.is_active=False;self.category.save()
        self.assertEqual(self.client.get(reverse('landing:product_detail',args=[self.product.pk])).status_code,404)
    def test_workflow_fills_blanks_and_preserves_custom_values(self):
        form=WorkflowForm({'reference_product':self.product.pk,'customer':'Cliente','quantity':2},instance=Entry(kind='quote',status='quoted'))
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['description'],self.product.description.strip())
        self.assertEqual(form.cleaned_data['product_category'],self.category)
        self.assertEqual(form.cleaned_data['unit_price'],D('12000'))
        form=WorkflowForm({'reference_product':self.product.pk,'title':'Personalizado','description':'Otro acabado','quantity':3,'unit_price':'0','unit_filament_g':'10','unit_print_hours':'2'})
        self.assertTrue(form.is_valid(),form.errors);self.assertEqual(form.cleaned_data['title'],'Personalizado');self.assertEqual(form.cleaned_data['unit_price'],0)
    def test_workflow_prefill_page_and_save_totals(self):
        self.login();response=self.client.get(reverse('management:workflow_create'),{'product':self.product.pk})
        self.assertEqual(response.context['form'].initial['title'],self.product.name)
        self.assertContains(response,'workflow-products')
        response=self.client.post(reverse('management:workflow_create'),{'reference_product':self.product.pk,'quantity':2,'customer':'Cliente','items-TOTAL_FORMS':'0','items-INITIAL_FORMS':'0'})
        self.assertEqual(response.status_code,302)
        entry=Entry.objects.get();self.assertEqual(entry.amount,D('24000'));self.assertEqual(entry.filament_g,D('50'));self.assertEqual(entry.print_hours,D('3'))
    def test_line_product_and_variant_relationship(self):
        form=QuoteItemForm({'product':self.product.pk,'quantity':2})
        self.assertTrue(form.is_valid(),form.errors);self.assertEqual(form.cleaned_data['unit_price'],D('12000'));self.assertEqual(form.cleaned_data['unit_filament_g'],D('25'))
        variant=ProductVariant.objects.create(product=self.product,name='Pequeña',length_cm=5,width_cm=4,height_cm=3,estimated_price=8000)
        form=QuoteItemForm({'variant':variant.pk,'quantity':1})
        self.assertTrue(form.is_valid(),form.errors);self.assertEqual(form.cleaned_data['product'],self.product);self.assertEqual(form.cleaned_data['unit_price'],D('8000'))
        other=Product.objects.create(name='Otro',mtm_category=self.category,price=1)
        form=QuoteItemForm({'product':other.pk,'variant':variant.pk,'quantity':1})
        self.assertFalse(form.is_valid());self.assertIn('variant',form.errors)
    def test_category_mismatch_rejected(self):
        other=CategoryProduct.objects.create(category_name='Otra')
        form=WorkflowForm({'reference_product':self.product.pk,'product_category':other.pk,'quantity':1})
        self.assertFalse(form.is_valid());self.assertIn('product_category',form.errors)
    def test_product_edit_without_new_consumption_fields_preserves_values(self):
        form=ProductForm({'name':self.product.name,'description':self.product.description,'price':12000,'mtm_category':self.category.pk,'is_active':'on'},instance=self.product)
        self.assertTrue(form.is_valid(),form.errors);product=form.save();self.assertEqual(product.unit_filament_g,D('25'))
    def test_payment_and_production_filters_are_independent(self):
        self.login()
        unpaid=Entry.objects.create(kind='order',status='printing',title='Sin pago',amount=100,paid_amount=0)
        partial=Entry.objects.create(kind='order',status='pending',title='Abono',amount=100,paid_amount=40)
        paid=Entry.objects.create(kind='order',status='printing',title='Pagado',amount=100,paid_amount=100)
        Entry.objects.create(kind='quote',status='quoted',title='Propuesta',amount=100)
        Entry.objects.create(kind='order',status='cancelled',title='Cancelado',amount=100)
        Entry.objects.create(kind='sale',status='sold',title='Sin cobro',amount=0)
        for value,ids in [('pending',[unpaid.pk,partial.pk]),('unpaid',[unpaid.pk]),('partial',[partial.pk]),('paid',[paid.pk])]:
            response=self.client.get(reverse('management:workflow'),{'payment':value})
            self.assertEqual(set(e.pk for e in response.context['page']),set(ids))
        response=self.client.get(reverse('management:workflow'),{'payment':'pending','status':'printing'})
        self.assertEqual([e.pk for e in response.context['page']],[unpaid.pk])
        self.assertContains(response,'payment=pending');self.assertContains(response,'status=printing')
        response=self.client.get(reverse('management:sales'),{'balance':'paid','status':'printing'})
        self.assertEqual([e.pk for e in response.context['page']],[paid.pk])

    def test_multiple_selected_products_keep_quantities_and_consumption(self):
        self.login()
        second=Product.objects.create(name='Segunda pieza',mtm_category=self.category,price=3000,unit_filament_g=10,unit_print_hours=D('0.5'))
        response=self.client.post(reverse('management:workflow_create'),{'title':'Dos productos','quantity':1,'unit_price':0,'unit_filament_g':0,'unit_print_hours':0,'items-TOTAL_FORMS':2,'items-INITIAL_FORMS':0,'items-0-product':self.product.pk,'items-0-quantity':2,'items-1-product':second.pk,'items-1-quantity':3})
        self.assertEqual(response.status_code,302)
        entry=Entry.objects.get();self.assertEqual(entry.amount,D('33000'));self.assertEqual(entry.filament_g,D('80'));self.assertEqual(entry.print_hours,D('4.5'))
        self.assertEqual(set(entry.items.values_list('product_id',flat=True)),{self.product.pk,second.pk})
    def test_catalog_image_is_copied_to_quote_and_staff_preview_is_private(self):
        import tempfile
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        with tempfile.TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            output=BytesIO();Image.new('RGB',(8,8),'green').save(output,format='PNG')
            self.product.image.save('catalog.png',SimpleUploadedFile('catalog.png',output.getvalue()),save=True)
            route=reverse('management:product_image',args=[self.product.pk])
            self.assertEqual(self.client.get(route).status_code,302)
            self.login();response=self.client.get(route);self.assertEqual(response.status_code,200);response.close()
            response=self.client.post(reverse('management:workflow_create'),{'reference_product':self.product.pk,'quantity':1,'items-TOTAL_FORMS':0,'items-INITIAL_FORMS':0})
            self.assertEqual(response.status_code,302)
            entry=Entry.objects.get();self.assertTrue(entry.image);self.assertNotEqual(entry.image.name,self.product.image.name)
            with entry.image.open('rb') as saved:self.assertEqual(saved.read(),output.getvalue())
