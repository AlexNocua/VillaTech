from django.db import migrations


def import_requests(apps, schema_editor):
    Contact = apps.get_model('landing', 'Contact')
    Entry = apps.get_model('management', 'Entry')
    database = schema_editor.connection.alias
    linked = Entry.objects.using(database).exclude(contact_id=None).values_list('contact_id',flat=True)
    for contact in Contact.objects.using(database).exclude(pk__in=linked).iterator():
        entry = Entry.objects.using(database).create(
            kind='quote',status='draft',source='web',contact_id=contact.pk,amount=0,
            title=f'Solicitud web · {contact.service}'[:150],description=contact.message,
            customer=contact.client_name[:150],customer_email=contact.email,
            customer_phone=str(contact.telephone),created_by_id=None)
        Entry.objects.using(database).filter(pk=entry.pk).update(created_at=contact.date_create)


class Migration(migrations.Migration):
    dependencies = [('management','0008_entry_contact_entry_customer_email_and_more')]
    # Preserve the imported rows on rollback; no historical emails are sent.
    operations = [migrations.RunPython(import_requests,migrations.RunPython.noop)]
