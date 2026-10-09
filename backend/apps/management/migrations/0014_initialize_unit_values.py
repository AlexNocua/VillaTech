from django.db import migrations
from django.db.models import F

def forward(apps,schema_editor):
    Entry=apps.get_model('management','Entry')
    # Existing totals remain unchanged. Old simple jobs are one unit of their saved amount.
    Entry.objects.all().update(unit_price=F('amount'),unit_filament_g=F('filament_g'),unit_print_hours=F('print_hours'))
class Migration(migrations.Migration):
    dependencies=[('management','0013_entry_approval_channel_entry_approval_nonce_and_more')]
    operations=[migrations.RunPython(forward,migrations.RunPython.noop)]
