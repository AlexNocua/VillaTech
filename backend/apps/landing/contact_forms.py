from django import forms
from django.core.exceptions import ValidationError
from pathlib import Path

class ContactForm(forms.Form):
    name=forms.CharField(max_length=255,error_messages={'required':'Escribe tu nombre.','max_length':'El nombre debe tener máximo 255 caracteres.'})
    phone=forms.RegexField(r'^\+?[0-9 ()-]{7,25}$',error_messages={'required':'Escribe tu teléfono.','invalid':'Usa números y, opcionalmente, +, espacios, paréntesis o guiones.'})
    email=forms.EmailField(max_length=254,error_messages={'required':'Escribe tu correo.','invalid':'Introduce un correo válido, por ejemplo nombre@correo.com.','max_length':'El correo debe tener máximo 254 caracteres.'})
    service=forms.ChoiceField(choices=[(v,v) for v in ['impresion-3d','diseno-prototipado','desarrollo-digital','otro']],error_messages={'required':'Selecciona un servicio.','invalid_choice':'Selecciona uno de los servicios disponibles.'})
    message=forms.CharField(max_length=500,error_messages={'required':'Describe tu idea.','max_length':'La descripción debe tener máximo 500 caracteres.'})
    privacy_consent=forms.ChoiceField(choices=[('accepted','accepted')],error_messages={'required':'Acepta el aviso de privacidad para enviar la solicitud.','invalid_choice':'Acepta el aviso de privacidad.'})

    def clean_phone(self):
        phone=self.cleaned_data['phone'].strip()
        digits=''.join(c for c in phone if c.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValidationError('Introduce un teléfono válido con entre 7 y 15 dígitos.')
        return phone

def validate_reference(file):
    if file.size>100*1024*1024: raise ValidationError('Cada archivo debe pesar máximo 100 MB.')
    if Path(file.name).suffix.lower() not in {'.stl','.obj','.3mf','.step','.stp','.pdf','.png','.jpg','.jpeg','.webp','.mp4','.webm','.mov'}:
        raise ValidationError('Formato de archivo no permitido.')

    extension = Path(file.name).suffix.lower()
    if extension in {'.mp4','.mov','.webm'}:
        try:
            header = file.read(32)
            valid = header.startswith(b'\x1a\x45\xdf\xa3') if extension == '.webm' else header[4:8] == b'ftyp'
            if not valid:
                raise ValidationError('Carga un video MP4, MOV o WEBM válido.')
        finally:
            file.seek(0)
