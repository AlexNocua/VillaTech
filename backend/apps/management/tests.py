from decimal import Decimal as D
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from .pricing import calculate
from .models import Entry
from .forms import VariantForm
from apps.landing.models import CategoryProduct, Product

class ManagementTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff=get_user_model().objects.create_user('staff',password='Test-only-Strong-732',is_staff=True)
        self.user=get_user_model().objects.create_user('customer',password='Test-only-Strong-732')
    def test_private_access(self):
        self.assertEqual(self.client.get('/gestion/').status_code,302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/gestion/').status_code,403)
    def test_staff_screens_and_timestamp(self):
        self.client.force_login(self.staff)
        for route in ['/gestion/','/gestion/registro/order/','/gestion/producto/','/gestion/variante/','/gestion/calculadora/']:
            self.assertEqual(self.client.get(route).status_code,200)
        self.client.post('/gestion/registro/sale/',{'title':'Figura','amount':'45000','filament_g':'100','acquired_filament_g':'0','category':'other','status':'pending'})
        entry=Entry.objects.get();self.assertEqual(entry.created_by,self.staff);self.assertIsNotNone(entry.created_at)
    def test_csrf(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.staff)
        self.assertEqual(c.post('/gestion/registro/sale/',{'title':'Forgery'}).status_code,403)
    def test_api_writes_forbidden(self):
        from django.urls import resolve
        from apps.inventary.api.views import ProductViewSet
        from rest_framework.test import APIRequestFactory
        request=APIRequestFactory().post('/api/products/',{'name':'Forgery'})
        response=ProductViewSet.as_view({'post':'create'})(request)
        self.assertIn(response.status_code,[401,403])
    def test_catalog_and_variants(self):
        cat=CategoryProduct.objects.create(category_name='Figuras')
        product=Product.objects.create(name='Referencia',mtm_category=cat,price=10000,is_public=True)
        self.assertEqual(product.category_slug,'figuras')
        from apps.landing.models import ProductVariant
        ProductVariant.objects.create(product=product,name='Pequeña',length_cm=5,width_cm=4,height_cm=8,estimated_price=35000)
        response=self.client.get('/')
        self.assertEqual(response.status_code,200);self.assertContains(response,'Pequeña');self.assertContains(response,'35000')
    def test_fake_image_rejected(self):
        form=VariantForm(data={},files={'image':SimpleUploadedFile('fake.png',b'<script>alert(1)</script>',content_type='image/png')})
        self.assertFalse(form.is_valid());self.assertIn('image',form.errors)
    def test_calculation(self):
        data={k:D(v) for k,v in dict(grams=100,spool_price=85000,spool_grams=1000,hours=5,printer_price=3000000,useful_hours=10000,maintenance_hour=200,watts=150,kwh_price=900,labor=5000,extras=1000,waste=10,margin=30).items()}
        result=calculate(data)
        self.assertEqual(result['material'],D('8500.00'))
        self.assertEqual(result['depreciation'],D('1500.00'))
        self.assertEqual(result['cost'],D('18842.50'))
        self.assertEqual(result['price'],D('26917.86'))
    def test_login_rate_limit(self):
        for _ in range(10):self.client.post('/gestion/ingresar/',{'username':'no','password':'no'})
        self.assertEqual(self.client.post('/gestion/ingresar/',{'username':'no','password':'no'}).status_code,429)
    def test_no_false_contact_success(self):
        response=self.client.post('/submit',{'name':'Incomplete'},follow=True)
        self.assertContains(response,'Revisa los campos',status_code=400)

    def test_private_product_publication(self):
        cat=CategoryProduct.objects.create(category_name='Privadas')
        p=Product.objects.create(name='Pieza interna única',mtm_category=cat,price=50000)
        self.assertNotContains(self.client.get('/'),'Pieza interna única')
        self.client.force_login(self.staff)
        self.client.post(f'/gestion/productos/{p.pk}/',{'name':p.name,'description':'','mtm_category':cat.pk,'price':50000,'stock':0,'is_active':'on','is_public':'on'})
        self.assertContains(self.client.get('/'),p.name)
    def test_quote_pdf_and_snapshot(self):
        from .models import QuoteItem
        from .quotation import build_quote
        order=Entry.objects.create(kind='order',title='Figura de prueba',customer='Cliente',amount=80000,created_by=self.staff)
        QuoteItem.objects.create(order=order,name='<Proyecto seguro>',length_cm=5,width_cm=4,height_cm=10,quantity=2,unit_price=40000)
        pdf=build_quote(order)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertEqual(self.client.get(f'/gestion/cotizacion/{order.pk}/pdf/').status_code,302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f'/gestion/cotizacion/{order.pk}/pdf/').status_code,200)
    def test_order_form_total(self):
        self.client.force_login(self.staff)
        response=self.client.post('/gestion/registro/order/',{'title':'Cotización completa','amount':'','filament_g':'0','acquired_filament_g':'0','status':'pending','category':'other','logo_theme':'light','items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'0','items-MIN_NUM_FORMS':'0','items-MAX_NUM_FORMS':'30','items-0-name':'Figura','items-0-length_cm':'6','items-0-width_cm':'5','items-0-height_cm':'12','items-0-quantity':'2','items-0-unit_price':'30000'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Entry.objects.get().amount,D('60000'))
    def test_energy_presets(self):
        from .models import PrinterProfile
        from .forms import CalculatorForm
        self.assertEqual(PrinterProfile.objects.get(name='Creality K1C').rated_watts,350)
        self.assertEqual(PrinterProfile.objects.get(name='Flashforge Creator 5 Pro').rated_watts,1200)

    def test_default_energy_and_measured_override(self):
        from .forms import CalculatorForm
        from .models import PrinterProfile
        self.client.force_login(self.staff)
        response=self.client.get('/gestion/calculadora/')
        self.assertEqual(response.context['form'].initial['energy_mode'],'rated')
        values={key:field.initial for key,field in CalculatorForm.base_fields.items()}
        profile=PrinterProfile.objects.get(name='Creality K1C')
        values.update(printer=profile.pk,energy_mode='rated',watts='1')
        form=CalculatorForm(values);self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['watts'],350)
        values.update(energy_mode='measured',watts='180')
        form=CalculatorForm(values);self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['watts'],D('180'))

    def test_printer_svg_markup_and_hero(self):
        import xml.etree.ElementTree as ET
        from django.template.loader import render_to_string
        svg=render_to_string('landing/components/printer-scene.html',{'printer_id':'test'})
        root=ET.fromstring(svg)
        self.assertEqual(root.tag,'svg')
        self.assertEqual(root.attrib['width'],'560')
        self.assertGreaterEqual(len(root.findall('.//path')),9)
        self.assertTrue(root.find('.//g[@data-print-layers]') is not None)
        self.assertContains(self.client.get('/'),'data-hero-orbit')
        self.assertContains(self.client.get('/'),'data-additive-printer',count=2)

    def test_colombian_numbers(self):
        from .templatetags.management_numbers import co_number
        self.assertEqual(co_number(D('1234567.89')),'1.234.567,89')
        self.assertEqual(co_number(D('1234567')),'1.234.567')
        self.assertEqual(co_number(D('-1200')),'-1.200')
        self.client.force_login(self.staff)
        Entry.objects.create(kind='sale',title='Figura',amount=1234567,created_by=self.staff)
        self.assertContains(self.client.get('/gestion/'),'1.234.567')

    def test_separate_operation_fields(self):
        self.client.force_login(self.staff)
        sale=self.client.get('/gestion/registro/sale/').context['form']
        expense=self.client.get('/gestion/registro/expense/').context['form']
        order=self.client.get('/gestion/registro/order/').context['form']
        self.assertNotIn('status',sale.fields)
        self.assertNotIn('logo_theme',sale.fields)
        self.assertIn('print_hours',sale.fields)
        self.assertEqual(set(expense.fields),{'title','category','amount'})
        self.assertIn('image',order.fields)
        self.assertIn('reference_product',order.fields)
        self.assertNotIn('category',order.fields)

    def test_sale_auto_sold_and_expense_ignores_other_fields(self):
        self.client.force_login(self.staff)
        self.client.post('/gestion/registro/sale/',{'title':'Figura','customer':'Cliente','amount':'123000','filament_g':'228','print_hours':'10','status':'pending'})
        sale=Entry.objects.get(kind='sale')
        self.assertEqual(sale.status,'sold');self.assertIsNotNone(sale.sold_at)
        self.assertEqual(sale.print_hours,D('10'))
        response=self.client.post('/gestion/registro/expense/',{'title':'Bobina','amount':'85000','category':'filament','customer':'IGNORADO','filament_g':'999','logo_theme':'dark'})
        self.assertEqual(response.status_code,302)
        expense=Entry.objects.get(kind='expense')
        self.assertEqual(expense.filament_g,0);self.assertEqual(expense.customer,'')

    def test_quote_then_order_then_sale_without_duplicate(self):
        self.client.force_login(self.staff)
        quote=Entry.objects.create(kind='quote',title='Proyecto',amount=80000,status='quoted',created_by=self.staff)
        self.assertEqual(self.client.get('/gestion/').context['sales'],0)
        self.assertEqual(self.client.get(f'/gestion/registro/{quote.pk}/convertir/order/').status_code,405)
        self.assertEqual(self.client.post(f'/gestion/registro/{quote.pk}/convertir/order/').status_code,302)
        quote.refresh_from_db();self.assertEqual(quote.kind,'order');self.assertEqual(quote.status,'pending')
        self.client.post(f'/gestion/registro/{quote.pk}/entrega/', {'status':'delivered'})
        self.assertEqual(self.client.post(f'/gestion/registro/{quote.pk}/convertir/sale/').status_code,400)
        quote.refresh_from_db();self.assertEqual(quote.status,'sold')
        self.assertEqual(self.client.post(f'/gestion/registro/{quote.pk}/convertir/sale/').status_code,400)
        self.assertEqual(Entry.objects.count(),1)
        self.assertEqual(self.client.get('/gestion/').context['sales'],D('80000'))
        blocked=Client(enforce_csrf_checks=True);blocked.force_login(self.staff)
        self.assertEqual(blocked.post(f'/gestion/registro/{quote.pk}/convertir/sale/').status_code,403)

    def test_quotation_without_calculator_generates_pdf(self):
        self.client.force_login(self.staff)
        response=self.client.post('/gestion/registro/quote/',{'title':'Proyecto','description':'Descripción de prueba','customer':'Cliente','amount':'125000','logo_theme':'dark','items-TOTAL_FORMS':'0','items-INITIAL_FORMS':'0','items-MIN_NUM_FORMS':'0','items-MAX_NUM_FORMS':'30'})
        self.assertEqual(response.status_code,302)
        quote=Entry.objects.get();self.assertEqual(quote.kind,'quote');self.assertEqual(quote.status,'quoted')
        self.assertTrue(quote.quotation_pdf)
        self.assertEqual(self.client.get(f'/gestion/cotizacion/{quote.pk}/pdf/').status_code,200)
        self.assertEqual(self.client.get('/gestion/').context['sales'],0)

    def test_estimate_optional_private_and_validated(self):
        from .forms import CalculatorForm
        from .models import PrinterProfile
        self.assertEqual(self.client.post('/gestion/calculadora/proceso/',{}).status_code,302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post('/gestion/calculadora/proceso/',{}).status_code,400)
        data={key:field.initial if field.initial is not None else '' for key,field in CalculatorForm.base_fields.items()}
        data['printer']=PrinterProfile.objects.get(name='Creality K1C').pk
        response=self.client.post('/gestion/calculadora/proceso/',data)
        self.assertEqual(response.status_code,200)
        self.assertIn('price',response.json()['result'])
        self.assertEqual(Entry.objects.count(),0)

    def test_development_project_images_private(self):
        from .models import DevelopmentProject, ProjectScreenshot
        self.assertEqual(self.client.get('/gestion/desarrollo/').status_code,302)
        self.client.force_login(self.staff)
        response=self.client.post('/gestion/desarrollo/',{'name':'Aplicativo de prueba','description':'Registro de información','project_type':'software','status':'active','customer':'Cliente'})
        self.assertEqual(response.status_code,302);self.assertEqual(DevelopmentProject.objects.count(),1)
        bad=SimpleUploadedFile('fake.png',b'<script>bad</script>',content_type='image/png')
        response=self.client.post('/gestion/desarrollo/',{'name':'No guardar','description':'Mala imagen','project_type':'web','status':'active','screenshots':bad})
        self.assertEqual(DevelopmentProject.objects.count(),1);self.assertContains(response,'válida')
        from io import BytesIO
        from PIL import Image
        data=BytesIO();Image.new('RGB',(10,10),'white').save(data,format='PNG')
        image=SimpleUploadedFile('reference.png',data.getvalue(),content_type='image/png')
        project=DevelopmentProject.objects.get()
        self.client.post(f'/gestion/desarrollo/{project.pk}/',{'name':project.name,'description':project.description,'project_type':'software','status':'active','screenshots':image})
        shot=ProjectScreenshot.objects.get()
        self.assertEqual(self.client.get(f'/gestion/desarrollo/captura/{shot.pk}/').status_code,200)
        self.client.logout();self.assertEqual(self.client.get(f'/gestion/desarrollo/captura/{shot.pk}/').status_code,302)

    def test_quote_total_limit(self):
        from .forms import QuoteFormSet
        entry=Entry(kind='quote',title='Límite',created_by=self.staff,amount=0)
        data={'items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'0','items-MIN_NUM_FORMS':'0','items-MAX_NUM_FORMS':'30','items-0-name':'Figura','items-0-quantity':'100000','items-0-unit_price':'9999999999.99'}
        formset=QuoteFormSet(data,instance=entry,prefix='items')
        self.assertFalse(formset.is_valid());self.assertIn('máximo',str(formset.non_form_errors()))

class CommercialBalanceTests(TestCase):
    def setUp(self):
        self.staff=get_user_model().objects.create_user('balance-staff',is_staff=True)
        self.client.force_login(self.staff)
    def test_confirmed_orders_count_without_payment_and_transition_does_not_duplicate(self):
        order=Entry.objects.create(kind='order',title='Pendiente',amount=100,status='printing')
        Entry.objects.create(kind='quote',title='Cotización',amount=500,status='quoted')
        Entry.objects.create(kind='order',title='Cancelado',amount=700,status='cancelled')
        response=self.client.get('/gestion/')
        self.assertEqual(response.context['sales'],100)
        self.assertEqual(response.context['collected'],0)
        self.assertEqual(response.context['receivable'],100)
        self.client.post(f'/gestion/registro/{order.pk}/abono/',{'payment':'30'})
        self.client.post(f'/gestion/registro/{order.pk}/convertir/sale/')
        response=self.client.get('/gestion/')
        self.assertEqual(response.context['sales'],100)
        self.assertEqual(response.context['collected'],30)
        self.assertEqual(response.context['receivable'],70)
        self.client.post(f'/gestion/registro/{order.pk}/abono/',{'payment':'71'})
        self.client.post(f'/gestion/registro/{order.pk}/abono/',{'payment':'NaN'})
        order.refresh_from_db(); self.assertEqual(order.paid_amount,30)
        self.assertEqual(order.payments.count(),1)
    def test_product_enable_is_idempotent_and_internal(self):
        category=CategoryProduct.objects.create(category_name='Figuras')
        order=Entry.objects.create(kind='order',title='Figura',amount=100,product_category=category)
        url=f'/gestion/registro/{order.pk}/producto/'
        self.client.post(url); self.client.post(url)
        order.refresh_from_db()
        self.assertEqual(Product.objects.count(),1)
        self.assertFalse(order.reference_product.is_public)
        self.assertEqual(order.reference_product.stock,0)
    def test_sales_and_stock_screens(self):
        for url in ['/gestion/ventas/','/gestion/productos/','/gestion/cotizaciones/','/gestion/pedidos/']:
            self.assertEqual(self.client.get(url).status_code,200)
    def test_stock_movements_record_actor_and_reject_negative_stock(self):
        category=CategoryProduct.objects.create(category_name='Llaveros')
        product=Product.objects.create(name='Llavero',price=5000,mtm_category=category,stock=2)
        url=f'/gestion/productos/{product.pk}/existencias/'
        self.client.post(url,{'quantity':'3','reason':'Compra'})
        self.client.post(url,{'quantity':'-2','reason':'Entrega'})
        self.client.post(url,{'quantity':'-4','reason':'Salida excesiva'})
        product.refresh_from_db(); self.assertEqual(product.stock,3)
        self.assertEqual(product.stock_movements.count(),2)
        self.assertEqual(product.stock_movements.first().created_by,self.staff)
