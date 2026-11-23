from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from pillow_heif import from_pillow

from apps.management.forms import WorkflowForm
from .contact_forms import validate_reference


class PhotoUploadTests(SimpleTestCase):
    def make_photo(self, extension, encoding, mode='RGB'):
        buffer = BytesIO()
        source = Image.new(mode, (48, 32))
        if encoding == 'HEIF':
            from_pillow(source).save(buffer)
        else:
            source.save(buffer, encoding)
        return SimpleUploadedFile(f'IMG_1234.{extension}', buffer.getvalue())

    def test_managed_photo_accepts_heic_and_stores_jpeg(self):
        upload = self.make_photo('HEIC', 'HEIF')
        field = WorkflowForm().fields['image']
        self.assertIn('.heic', field.widget.attrs['accept'])
        photo = field.clean(upload)
        self.assertEqual(photo.name, 'IMG_1234.jpg')
        self.assertEqual(Image.open(photo).format, 'JPEG')

    def test_public_contact_converts_supported_formats(self):
        for extension, encoding in (
            ('heif', 'HEIF'), ('jpg', 'JPEG'), ('jpeg', 'JPEG'), ('png', 'PNG'), ('webp', 'WEBP'),
            ('avif', 'AVIF'), ('gif', 'GIF'), ('bmp', 'BMP'), ('tif', 'TIFF'), ('tiff', 'TIFF'),
        ):
            with self.subTest(extension=extension):
                photo = validate_reference(self.make_photo(extension, encoding))
                with Image.open(photo) as decoded:
                    self.assertEqual(decoded.format, {'png': 'PNG', 'webp': 'WEBP'}.get(extension, 'JPEG'))

    def test_alpha_and_invalid_upload(self):
        photo = validate_reference(self.make_photo('tiff', 'TIFF', 'RGBA'))
        self.assertEqual(photo.content_type, 'image/webp')
        self.assertEqual(Image.open(photo).mode, 'RGBA')
        invalid = SimpleUploadedFile('fake.heic', b'Not an image')
        with self.assertRaises(ValidationError):
            WorkflowForm().fields['image'].clean(invalid)

    def test_large_original_has_a_specific_error(self):
        upload = self.make_photo('jpg', 'JPEG')
        upload.size = 26 * 1024 * 1024
        with self.assertRaisesMessage(ValidationError, '25 MB'):
            validate_reference(upload)
