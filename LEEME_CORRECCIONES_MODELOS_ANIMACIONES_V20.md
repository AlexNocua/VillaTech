# VillaTech — correcciones V20

## Animaciones de escritorio

La sección de opiniones estaba marcada con `data-story-stop`, antes de Preguntas y Lanzamiento. Esto ocultaba permanentemente la escena al pasar por opiniones. Ahora es una pausa temporal (`data-story-break`), como el catálogo; la secuencia continúa después. Contacto conserva la marca de final. También se actualiza el límite de la escena cuando cambia la altura de la página, por ejemplo al desplegar más opiniones.

## Modelos

- Guardar no interpreta la geometría: se almacena el original y la vista previa se solicita separadamente.
- Errores de escritura o base de datos durante el guardado se registran con detalle en los logs. El usuario recibe un mensaje, conserva título y descripción y puede seleccionar el archivo de nuevo. Se retira el archivo nuevo si falló su registro en base de datos.
- Carga con progreso, validación previa STL/3MF hasta 100 MB y bloqueo de doble clic. Los fallos de red, tamaño, sesión o servidor no borran los campos.
- La lectura y recorrido geométrico de la vista previa tienen un presupuesto de 8 segundos. Si se supera, devuelve un mensaje controlado; el original permanece disponible para descargar. En el navegador, la solicitud de vista previa también tiene un límite de espera.

Sin el archivo que falló ni los logs de producción no puede atribuirse el incidente concreto a falta de almacenamiento, tiempo de espera u otra causa. Estas correcciones cubren los fallos detectados en el código; no cambian cuotas ni límites del alojamiento. Si persiste, consulta los logs en el momento de la carga y comparte el traceback sin credenciales.

## Instalar

Conservar base de datos, archivos subidos y variables de producción. Actualizar código y ejecutar desde la raíz:

```sh
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reiniciar el servicio. No se añaden migraciones en V20; migrate aplica las pendientes anteriores. Los scripts modificados tienen versión de caché 20.

## Validar

```sh
python backend/manage.py test apps.management apps.landing --noinput
node tests/public-listings.cjs
node tests/model-upload.cjs
```

En un navegador de escritorio, bajar por opiniones, preguntas y lanzamiento. Comprobar tanto con opiniones publicadas como sin ellas y después de usar «Ver más». Subir el modelo que falló y abrir la vista previa separadamente. La revisión visual en navegador real y la reproducción con ese modelo quedan pendientes.
