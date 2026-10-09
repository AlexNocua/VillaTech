from django import forms
from django.core.exceptions import ValidationError
from pathlib import Path

class ContactForm(forms.Form):
    name=forms.CharField(max_length=255)
    phone=forms.RegexField(r'^\+?[0-9 ()-]{7,25}$')
    email=forms.EmailField()
    service=forms.ChoiceField(choices=[(v,v) for v in ['impresion-3d','diseno-prototipado','desarrollo-digital','otro']])
    message=forms.CharField(max_length=500)
    privacy_consent=forms.ChoiceField(choices=[('accepted','accepted')])

    def clean_phone(self):
        phone=self.cleaned_data['phone'].strip()
        digits=''.join(c for c in phone if c.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValidationError('Introduce un teléfono válido con entre 7 y 15 dígitos.')
        return phone

def validate_reference(file):
    if file.size>15*1024*1024: raise ValidationError('Cada archivo debe pesar máximo 15 MB.')
    if Path(file.name).suffix.lower() not in {'.stl','.obj','.3mf','.step','.stp','.pdf','.png','.jpg','.jpeg','.webp'}:
        raise ValidationError('Formato de archivo no permitido.')
