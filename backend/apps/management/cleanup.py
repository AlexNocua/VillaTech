"""Remove only files owned by the selected commercial record after DB commit."""
import logging
from django.db import transaction


def delete_commercial_entry(entry):
    files = [entry.image, entry.quotation_pdf]
    for item in entry.items.all():
        files.extend([item.image, item.comparison_image])
    files.extend(email.attachment for email in entry.emails.all())
    owned = {(f.storage, f.name) for f in files if f and f.name}
    entry.delete()  # Items, payments and operational mails cascade; reports remain.
    def remove_files():
        for storage, name in owned:
            try:
                storage.delete(name)
            except Exception:
                logging.getLogger(__name__).warning('No se pudo limpiar un archivo del registro eliminado')
    transaction.on_commit(remove_files)
