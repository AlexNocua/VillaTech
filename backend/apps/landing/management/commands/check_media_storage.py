import os
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Comprueba ubicación persistente y escritura/lectura de media al arrancar.'

    def handle(self, *args, **options):
        root = Path(settings.MEDIA_ROOT).resolve()
        if settings.IS_RAILWAY:
            mount = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '').strip()
            if not mount:
                raise CommandError('Conecta un volumen al servicio Django (por ejemplo /data). Railway no informa RAILWAY_VOLUME_MOUNT_PATH; media no sería persistente.')
            if not root.is_relative_to(Path(mount).resolve()):
                raise CommandError('MEDIA_ROOT debe estar dentro del volumen Railway: ' + mount)
        try:
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=root, prefix='.media-check-') as probe:
                probe.write(b'villatech-media'); probe.flush()
                probe.seek(0)
                if probe.read() != b'villatech-media':
                    raise OSError('No se pudo leer la prueba de escritura.')
        except OSError as error:
            raise CommandError('Media no escribible en ' + str(root) + '. Revisa permisos (RAILWAY_RUN_UID=0), espacio y volumen. ' + type(error).__name__)
        self.stdout.write(self.style.SUCCESS('Media: escritura y lectura correctas en ' + str(root)))
