from django import forms
from .models import Entry
from apps.landing.models import Product, ProductVariant

class EntryForm(forms.ModelForm):
    """Shared validation only; each operation exposes its own fields."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for name in ['filament_g','print_hours']:
            if name in self.fields:self.fields[name].required=False
        if 'logo_theme' in self.fields:self.fields['logo_theme'].required=False
        if 'reference_product' in self.fields:
            self.fields['reference_product'].queryset=Product.objects.select_related('mtm_category').all()
    def clean_logo_theme(self):return self.cleaned_data.get('logo_theme') or 'light'
    def clean_filament_g(self):return self.cleaned_data.get('filament_g') or 0
    def clean_print_hours(self):return self.cleaned_data.get('print_hours') or 0
    def clean(self):
        data=super().clean()
        product=data.get('reference_product');category=data.get('product_category')
        if product and not category:data['product_category']=product.mtm_category
        if product and category and product.mtm_category_id != category.pk:
            self.add_error('product_category','La categoría debe coincidir con el producto de referencia.')
        if self.instance.pk and data.get('amount') is not None and data['amount'] < self.instance.paid_amount:
            self.add_error('amount','El total no puede ser menor que los abonos registrados.')
        if data.get('status') == 'cancelled' and self.instance.paid_amount:
            self.add_error('status','Este pedido tiene abonos. Revisa y concilia los pagos antes de cancelar.')
        if self.instance.pk and self.instance.status in ('delivered','cancelled') and data.get('status') and data['status'] != self.instance.status:
            self.add_error('status','El pedido está cerrado; conserva su estado para no reabrir su historial.')
        return data
    class Meta:
        model=Entry
        fields=[]

class SaleForm(EntryForm):
    class Meta(EntryForm.Meta):
        fields=['title','description','customer','product_category','reference_product','amount','filament_g','print_hours']
        labels={'title':'Producto vendido','amount':'Precio de venta total (COP)'}
        widgets={'description':forms.Textarea(attrs={'rows':3})}

class OrderForm(EntryForm):
    class Meta(EntryForm.Meta):
        fields=['title','description','customer','product_category','reference_product','customer_email','customer_phone','amount','status','estimated_delivery_date','filament_g','print_hours','image','logo_theme']
        labels={'title':'Producto / proyecto solicitado','amount':'Precio total (COP, si no detallas productos)'}
        widgets={'description':forms.Textarea(attrs={'rows':3}),'estimated_delivery_date':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['amount'].required=False
        if 'status' in self.fields:self.fields['status'].choices=[choice for choice in Entry.STATUS if choice[0] in ['pending','printing','ready','delivered','cancelled']]
        self.fields['estimated_delivery_date'].help_text='Vacío al confirmar: estimación automática según cola y horas. Puedes ajustar el compromiso con el cliente.'
    def clean_amount(self):
        value=self.cleaned_data.get('amount');product=self.cleaned_data.get('reference_product')
        return product.price if value is None and product else value or 0
    def clean_estimated_delivery_date(self):
        from django.utils import timezone
        value = self.cleaned_data.get('estimated_delivery_date')
        if value and value < timezone.localdate() and not self.instance.approved_at:
            raise forms.ValidationError('Confirma una entrega para hoy o una fecha futura.')
        return value

class QuotationForm(OrderForm):
    class Meta(OrderForm.Meta):
        fields=[name for name in OrderForm.Meta.fields if name!='status']

class DeliveryForm(forms.Form):
    estimated_delivery_date = forms.DateField(label='Entrega estimada', required=False,
        widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    status = forms.ChoiceField(label='Estado de producción',choices=[c for c in Entry.STATUS if c[0] in ('pending','printing','ready','delivered','cancelled')])

class ApprovalForm(forms.Form):
    estimated_delivery_date = forms.DateField(label='Entrega estimada', required=False,
        widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    def clean_estimated_delivery_date(self):
        from django.utils import timezone
        date = self.cleaned_data.get('estimated_delivery_date')
        if date and date < timezone.localdate():
            raise forms.ValidationError('La confirmación debe proponer hoy o una fecha futura.')
        return date

class ExpenseForm(forms.ModelForm):
    class Meta:
        model=Entry
        fields=['title','category','amount']
        labels={'title':'¿En qué gastaste?','amount':'Valor del gasto (COP)'}

class ProductForm(forms.ModelForm):
    def save(self, commit=True):
        from pathlib import Path
        uploaded=self.cleaned_data.get('print_model')
        if uploaded and hasattr(uploaded,'content_type'):
            self.instance.print_model_original_name=Path(uploaded.name).name[:255]
        return super().save(commit=commit)
    class Meta:
        model = Product
        fields = ['name','description','mtm_category','price','image','image_url','print_model','is_active','is_public']
        widgets={'print_model':forms.FileInput(attrs={'accept':'.stl,.obj,.3mf,.step,.stp,.gcode'})}
        help_texts={'print_model':'Hasta 100 MB. STL, OBJ, 3MF, STEP/STP o GCODE. Si no eliges otro archivo, se conserva el modelo guardado.'}

class VariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['product','name','length_cm','width_cm','height_cm','estimated_price','image','is_active']

class CalculatorForm(forms.Form):
    energy_mode=forms.ChoiceField(initial='rated',label='Método de energía',choices=[('rated','Perfil oficial: estimación conservadora'),('measured','Personalizar: potencia media medida')])
    printer = forms.ModelChoiceField(queryset=__import__("apps.management.models",fromlist=["PrinterProfile"]).PrinterProfile.objects.all(),label="Perfil de impresora",required=False)
    grams = forms.DecimalField(label='Consumo total del laminador (g)', min_value=0, max_value=100000, initial=100)
    spool_price = forms.DecimalField(label='Costo de la bobina (COP)', min_value=0, max_value=100000000, initial=85000)
    spool_grams = forms.DecimalField(label='Peso de la bobina (g)', min_value=1, max_value=100000, initial=1000)
    hours = forms.DecimalField(label='Horas de impresión', min_value=0, max_value=10000, initial=5)
    printer_price = forms.DecimalField(label='Costo de la impresora (COP)', min_value=0, max_value=100000000, initial=3000000)
    useful_hours = forms.DecimalField(label='Vida útil estimada (horas)', min_value=1, max_value=100000, initial=10000)
    maintenance_hour = forms.DecimalField(label='Reserva de mantenimiento por hora (COP)', min_value=0, max_value=100000, initial=200)
    watts = forms.DecimalField(label='Potencia media medida (W)', min_value=0, max_value=10000, initial=None,required=False)
    kwh_price = forms.DecimalField(label='Tarifa eléctrica COP/kWh', min_value=0, max_value=100000, initial=900)
    labor = forms.DecimalField(label='Trabajo, diseño y acabado (COP)', min_value=0, max_value=100000000, initial=5000)
    extras = forms.DecimalField(label='Empaque y otros costos (COP)', min_value=0, max_value=100000000, initial=1000)
    waste = forms.DecimalField(label='Reserva por fallos (%)', min_value=0, max_value=100, initial=10)
    margin = forms.DecimalField(label='Margen sobre precio de venta (%)', min_value=0, max_value=95, initial=30)

    def clean(self):
        data=super().clean();printer=data.get('printer')
        if data.get('energy_mode')=='rated':
            if not printer or not printer.rated_watts:self.add_error('printer','Elige una impresora con potencia nominal configurada.')
            else:data['watts']=printer.rated_watts
        elif data.get('watts') is None:self.add_error('watts','Introduce la potencia media medida para calcular energía.')
        return data


from django.forms import inlineformset_factory
from .models import PrinterProfile, QuoteItem
from apps.landing.models import CategoryProduct

class CategoryForm(forms.ModelForm):
    class Meta:
        model=CategoryProduct
        fields=['category_name','is_active']

class PrinterForm(forms.ModelForm):
    class Meta:
        model=PrinterProfile
        fields=['name','rated_watts','average_watts','purchase_price','useful_hours','maintenance_hour']

class QuoteItemForm(forms.ModelForm):
    class Meta:
        model=QuoteItem
        fields=['variant','name','length_cm','width_cm','height_cm','quantity','unit_price','unit_filament_g','unit_print_hours','description','image','comparison_image']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in ['name','length_cm','width_cm','height_cm','unit_price','unit_filament_g','unit_print_hours']:
            self.fields[field].required=False
            if not self.instance.pk:self.initial[field]=''
        self.fields['variant'].label='Referencia interna por tamaño (opcional)'
    def clean_quantity(self):
        value=self.cleaned_data['quantity']
        if value>1000000:raise forms.ValidationError('Máximo 1000000 unidades por línea.')
        return value
    def clean(self):
        data=super().clean();variant=data.get('variant')
        if variant:
            data['name']=data.get('name') or f'{variant.product.name} · {variant.name}'
            for field in ['length_cm','width_cm','height_cm']:data[field]=data.get(field) if data.get(field) is not None else getattr(variant,field)
            data['unit_price']=data.get('unit_price') if data.get('unit_price') is not None else variant.estimated_price
        if not data.get('name') and not data.get('DELETE'): self.add_error('name','Escribe un producto o elige una referencia.')
        for field in ['length_cm','width_cm','height_cm','unit_price','unit_filament_g','unit_print_hours']:data[field]=data.get(field) or 0
        return data

from django.forms.models import BaseInlineFormSet
from decimal import Decimal
class QuoteItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):return
        total=sum((form.cleaned_data.get('quantity',0)*form.cleaned_data.get('unit_price',0) for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE')),Decimal(0))
        if total>Decimal('999999999999.99'):raise forms.ValidationError('El total supera el máximo permitido para el registro.')

QuoteFormSet=inlineformset_factory(Entry,QuoteItem,form=QuoteItemForm,formset=QuoteItemFormSet,extra=1,can_delete=True,max_num=30,validate_max=True)

from .models import DevelopmentProject
class DevelopmentForm(forms.ModelForm):
    class Meta:
        model=DevelopmentProject
        fields=['name','project_type','description','customer','status','started_on']
        widgets={'description':forms.Textarea(attrs={'rows':5}),'started_on':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}

class WorkflowForm(EntryForm):
    class Meta(EntryForm.Meta):
        fields=['title','description','customer','customer_email','customer_phone','product_category','reference_product',
                'quantity','unit_price','unit_filament_g','unit_print_hours','estimated_delivery_date','image','logo_theme']
        labels={'title':'Nombre del trabajo','description':'Descripción y condiciones', 'estimated_delivery_date':'Entrega propuesta'}
        widgets={'description':forms.Textarea(attrs={'rows':3}),'estimated_delivery_date':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['quantity'].max_value=1000000
        self.fields['description'].help_text='Material, color, acabado y condiciones acordadas con el cliente.'
        self.fields['estimated_delivery_date'].help_text='Opcional. Al aprobar se propone una fecha si no la registras.'
    def clean(self):
        data=super().clean()
        from decimal import Decimal
        if data.get('quantity') and data.get('unit_price') is not None:
            if data['quantity']*data['unit_price'] > Decimal('999999999999.99'):
                self.add_error('unit_price','El total supera el valor permitido.')
        return data
