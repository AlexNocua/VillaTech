"""Decode raster uploads and store a browser-compatible image."""
from io import BytesIO
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener(decode_threads=1, thumbnails=False, depth_images=False, aux_images=False)

PHOTO_EXTENSIONS = frozenset({
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.avif',
    '.gif', '.bmp', '.tif', '.tiff',
})
PHOTO_ACCEPT = 'image/*,' + ','.join(sorted(PHOTO_EXTENSIONS))
PHOTO_FORMATS = ('JPEG', 'PNG', 'WEBP', 'HEIF', 'AVIF', 'GIF', 'BMP', 'TIFF')
MAX_PHOTO_BYTES = 25 * 1024 * 1024
MAX_PHOTO_PIXELS = 55_000_000
MAX_STORED_BYTES = 5 * 1024 * 1024


def prepare_photo(upload):
    if upload.size > MAX_PHOTO_BYTES:
        raise ValidationError('La foto original no puede superar 25 MB.')
    try:
        upload.seek(0)
        with Image.open(upload, formats=PHOTO_FORMATS) as source:
            if source.width * source.height > MAX_PHOTO_PIXELS:
                raise ValidationError('La foto no puede superar 55 megapíxeles.')
            original_formats = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
            if (upload.size <= MAX_STORED_BYTES and source.width * source.height <= 20_000_000
                    and original_formats.get(Path(upload.name).suffix.lower()) == source.format):
                source.verify()
                return upload
            source.load()
            alpha = source.has_transparency_data
            oriented = ImageOps.exif_transpose(source)
            oriented.thumbnail((3000, 3000))
            pixels = oriented.convert('RGBA' if alpha else 'RGB')
            pixels.info.clear()
            suffix, mime, fmt = ('webp', 'image/webp', 'WEBP') if alpha else ('jpg', 'image/jpeg', 'JPEG')
            for edge in (3000, 2200, 1600):
                pixels.thumbnail((edge, edge))
                output = BytesIO()
                pixels.save(output, fmt, quality=86)
                if output.tell() <= MAX_STORED_BYTES:
                    return SimpleUploadedFile(
                        f'{Path(upload.name).stem[:120]}.{suffix}', output.getvalue(), mime,
                    )
            raise ValidationError('No pudimos reducir el tamaño de la foto. Intenta con una resolución menor.')
    except (OSError, ValueError, SyntaxError, RuntimeError, EOFError, Image.DecompressionBombError) as exc:
        raise ValidationError(
            'La foto no es válida o no se pudo abrir. Usa HEIC/HEIF, JPG, PNG, WEBP, AVIF, GIF, BMP o TIFF.'
        ) from exc
    finally:
        upload.seek(0)


class PhotoFormField(forms.ImageField):
    def to_python(self, data):
        if not data:
            return super().to_python(data)
        return super().to_python(prepare_photo(data))

    def widget_attrs(self, widget):
        return {**super().widget_attrs(widget), 'accept': PHOTO_ACCEPT}


class PhotoField(models.ImageField):
    def formfield(self, **kwargs):
        return super().formfield(form_class=PhotoFormField, **kwargs)

    def deconstruct(self):
        # Same storage and schema as Django ImageField; only the upload form changes.
        name, _, args, kwargs = super().deconstruct()
        return name, 'django.db.models.ImageField', args, kwargs
