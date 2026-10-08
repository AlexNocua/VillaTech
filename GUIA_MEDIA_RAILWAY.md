# Imágenes y media — corrección VillaTech

## Qué se corrigió

- Producto principal: ahora admite subir una imagen local; antes solo tenía una URL externa y el formulario no incluía un archivo. La imagen subida tiene prioridad sobre la URL existente.
- Edición del producto: recibe request.FILES.
- Catálogo: sirve archivos de productos y variantes publicadas y activas, con categoría activa. Un archivo ausente responde 404 en lugar de 500. Los adjuntos privados conservan su acceso autenticado.
- MEDIA_ROOT: respeta una ruta explícita y, si no existe, usa la carpeta media dentro del volumen que Railway informa.
- Arranque: prueba escritura y lectura con un archivo temporal que luego elimina. En Railway exige que MEDIA_ROOT esté dentro del volumen adjunto. No se realiza esta comprobación en predeploy porque el volumen no está montado allí.
- Formulario público: registra en logs las excepciones al guardar solicitudes/archivos, para que un error de permisos o espacio no quede oculto.

## Pasos obligatorios en Railway

1. En el servicio Django, confirma un volumen persistente conectado. El volumen de PostgreSQL NO almacena las imágenes de Django.
2. Para una instalación con volumen montado en /data, configura:

```env
MEDIA_ROOT=/data/media
RAILWAY_RUN_UID=0
```

Si el volumen actual está montado en otra ruta, conserva ese volumen y usa MEDIA_ROOT dentro de él. No cambies ni borres el volumen con archivos existentes. Si no defines MEDIA_ROOT, el código elige <ruta-del-volumen>/media. Si el volumen ya se monta directamente en /data/media, define MEDIA_ROOT=/data/media para no agregar otra subcarpeta.

RAILWAY_VOLUME_MOUNT_PATH lo proporciona Railway automáticamente: no lo inventes ni lo agregues manualmente para simular un volumen.

3. Integra este código y la nueva migración landing/0008_product_image.py en tu repositorio y despliega. El predeploy existente aplica migrate; conserva el start command sh /app/deploy/start-railway.sh para ejecutar la comprobación de media.
4. En los logs debe aparecer: Media: escritura y lectura correctas en /data/media (o tu ruta).
5. Sube una imagen en gestión, productos; una variante; un pedido/cotización o un proyecto. Abre las imágenes, reinicia o redespliega y confirma que siguen disponibles.
6. Si cambiaste MEDIA_ROOT desde otra carpeta persistente, copia los archivos preservando sus rutas relativas catalog/, private/ y Files/ antes de retirar la ubicación anterior. La BD guarda nombres relativos, no el contenido de los archivos.

## Diagnóstico desde una shell del servicio desplegado

```sh
cd /app/backend
python manage.py check_media_storage
python manage.py shell -c "from django.conf import settings; print(settings.MEDIA_ROOT)"
python manage.py shell -c "from apps.landing.models import ProductVariant; print([(v.pk, bool(v.image) and v.image.storage.exists(v.image.name)) for v in ProductVariant.objects.exclude(image='')])"
```

Si aparece PermissionError, comprueba RAILWAY_RUN_UID y permisos. Si aparece falta de volumen o ruta fuera del volumen, revisa la conexión y montaje en el servicio Django. Si el disco está lleno, revisa capacidad del volumen.

## Archivos anteriores

Esta corrección no recupera imágenes borradas por un despliegue anterior sin volumen. Si la BD conserva el nombre pero el archivo no existe, restáuralo desde un respaldo o vuelve a subirlo. No sustituye el nombre por una imagen vacía ni borra registros.

## Verificación realizada

35 pruebas Django de landing y gestión pasaron, incluidas nuevas pruebas de guardado real de imagen al editar un producto, lectura pública autorizada, restricción de publicación, variante, archivo ausente y comprobación de volumen/escritura. Django check y makemigrations --check no detectan problemas. La persistencia tras un despliegue real debe comprobarse en tu servicio Railway; no se tuvo acceso a él.
