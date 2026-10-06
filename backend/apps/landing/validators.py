from pathlib import Path
from uuid import uuid4
from django.core.exceptions import ValidationError
from PIL import Image

def image_path(instance, filename):
    return 'catalog/' + uuid4().hex + Path(filename).suffix.lower()

def private_path(instance, filename):
    return 'private/' + uuid4().hex + Path(filename).suffix.lower()

def validate_image(file):
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('La imagen no puede superar 5 MB.')
    try:
        image = Image.open(file)
        if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 20000000:
            raise ValueError()
        image.verify()
    except Exception:
        raise ValidationError('Carga una imagen PNG, JPG o WEBP válida.')
    finally:
        file.seek(0)
