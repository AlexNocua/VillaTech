from django.db import migrations

def setup(apps,schema_editor):
    Category=apps.get_model('landing','CategoryProduct')
    Entry=apps.get_model('management','Entry')
    for name in ['Llaveros','Técnicos','Figuras']:
        if not Category.objects.filter(category_name__iexact=name).exists():Category.objects.create(category_name=name)
    for entry in Entry.objects.filter(kind='sale'):
        entry.status='sold'
        entry.sold_at=entry.sold_at or entry.created_at
        entry.save(update_fields=['status','sold_at'])

class Migration(migrations.Migration):
    dependencies=[('management','0005_entry_description_entry_print_hours_and_more')]
    operations=[migrations.RunPython(setup,migrations.RunPython.noop)]
