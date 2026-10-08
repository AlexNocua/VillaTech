from django.db import migrations, models
import apps.landing.validators

class Migration(migrations.Migration):
    dependencies = [('landing', '0007_contactemail')]
    operations = [migrations.AddField(model_name='product', name='image', field=models.ImageField(blank=True, upload_to=apps.landing.validators.image_path, validators=[apps.landing.validators.validate_image], verbose_name='Imagen del producto'))]
