from datetime import timedelta
from django.db import migrations
from django.utils import timezone


def repair_windows(apps, schema_editor):
    Entry = apps.get_model('management', 'Entry')
    Email = apps.get_model('management', 'OperationalEmail')
    for entry in Entry.objects.filter(kind='quote',status__in=['sent','expired']).iterator():
        message = Email.objects.filter(entry_id=entry.pk,event_key=f'quote:{entry.pk}:{entry.approval_nonce}').first()
        if not message:
            continue
        if message.status == 'sent' and message.sent_at:
            entry.quote_sent_at = message.sent_at
            entry.quote_expires_at = message.sent_at + timedelta(hours=48)
            entry.status = 'sent' if entry.quote_expires_at > timezone.now() else 'expired'
        elif message.status in ('pending','failed'):
            entry.quote_sent_at = entry.quote_expires_at = None
            entry.status = 'sent'
        else:
            continue
        entry.save(update_fields=['quote_sent_at','quote_expires_at','status'])


class Migration(migrations.Migration):
    dependencies = [('management', '0015_entry_delivery_settled_amount_and_more')]
    operations = [migrations.RunPython(repair_windows, migrations.RunPython.noop)]
