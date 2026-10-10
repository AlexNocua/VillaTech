# VillaTech — referencias multimedia y modelos de impresión V11

## Actualizar
Desde la raíz del proyecto:

```bash
python backend/manage.py migrate --noinput
python backend/manage.py collectstatic --noinput
python backend/manage.py check
```

Dentro de /app/backend usa python manage.py. Reinicia el servicio después de actualizar. Se agregan las migraciones landing 0010 (nombre original de los adjuntos) y 0011 (modelo de impresión del producto). No cambies las credenciales Gmail ni la clave de firma ni borres la base existente. Los archivos privados necesitan el volumen persistente de MEDIA_ROOT ya usado por el proyecto.

## Formulario del cliente
Hasta 5 archivos; máximo 100 MB por archivo y 200 MB entre todos los adjuntos. Es un máximo, no un tamaño mínimo: también se permiten archivos pequeños. Videos MP4, WEBM y MOV, además de STL, OBJ, 3MF, STEP/STP, PDF, PNG, JPG y WEBP. Se comprueba el tamaño en el navegador y el servidor; los videos también deben tener una cabecera compatible con su contenedor. No se realiza transcodificación ni análisis del códec.

Los archivos grandes se reciben mediante el almacenamiento temporal de Django; no se aumenta el límite de archivos en memoria. El tamaño permitido de datos de solicitud se ajustó a 210 MB. Si hay un proxy externo con un límite de cuerpo o un tiempo de espera inferior, debe permitir el envío multipart completo de hasta 200 MB más sus datos de formulario. La configuración del proxy externo no está incluida en este proyecto.

## Consultar el pedido
En la operación se ve la información general y el número de adjuntos. Al abrir la ficha aparece Lo que envió el cliente: descripción, contacto, imágenes con vista previa, videos con controles y descarga de documentos o modelos. Las descargas y vistas previas requieren una sesión de gestión autorizada. Los videos admiten solicitudes por rangos de bytes para poder desplazarse por la reproducción. La compatibilidad depende del navegador y el códec; si MOV u otro video no se reproduce, puede descargarse. No se expone el directorio privado públicamente ni se adjuntan videos grandes al correo.

Los adjuntos nuevos conservan el nombre original. Los archivos anteriores siguen accesibles; si el nombre original no estaba registrado, se muestra el nombre almacenado. Las solicitudes antiguas con un único archivo conservan su descarga y pueden verse en la ficha si son imagen o video reconocido.

## Modelo de impresión en productos
En Inventario, crea o edita un producto y carga Modelo de impresión: STL, OBJ, 3MF, STEP/STP o GCODE de hasta 100 MB. Se conserva un modelo actual por producto, de forma privada. Al editar sin seleccionar un archivo nuevo se mantiene el anterior. El inventario y la edición muestran su descarga; la ficha del pedido también la muestra si su producto de referencia tiene modelo. Los archivos se almacenan para descargar; no se ejecutan, imprimen ni visualizan en 3D automáticamente.

## Pruebas
Se verifican tamaños, formatos, límite combinado, persistencia y nombre del archivo, vistas previas, permisos, reproducción por rangos y conservación del modelo al editar. La versión se entrega para desplegar; no se han subido archivos ni modificado pedidos en producción. Los toast y los datos del formulario ante errores se conservan.
