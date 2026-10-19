# VillaTech V19 — catálogo y opiniones

## Cambios

- Se muestran cinco productos y cinco opiniones inicialmente. Si hay más, «Ver más» despliega todos los resultados de la categoría/búsqueda actual; «Ver menos» vuelve a cinco.
- Los contadores reflejan los resultados del filtro. Cambiar categoría, búsqueda u orden restablece el límite inicial.
- Las opiniones publicadas ya no se recortan a 24; están disponibles todas las autorizadas y publicadas. Se conserva la moderación y la separación entre impresión 3D y software.
- Los filtros y el despliegue de opiniones funcionan independientemente de Anime.js. Sin JavaScript se muestran todos los registros como alternativa accesible.
- Escena CSS 3D con cubo de seis caras, portátil en perspectiva, estrellas y mensajes animados con Anime.js local. Incluye pausa, movimiento reducido y pausa de animaciones ambientales cuando la sección no está visible.
- La escena ajusta su escala al ancho disponible. Mejoras en rejillas, textos largos, filtros, tarjetas y controles táctiles para pantallas pequeñas.

## Actualizar

Conserva tu configuración de producción, credenciales, archivos subidos y base de datos. No reemplaces estos datos con archivos de otra instalación. Instala el código actualizado y ejecuta, desde la raíz del proyecto:

```sh
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reinicia la aplicación. V19 no agrega migraciones; `migrate` aplica las que estén pendientes de versiones anteriores. Los recursos modificados usan la versión de caché 19.

## Comprobación

```sh
python backend/manage.py test apps.management apps.landing --noinput
node tests/public-listings.cjs
```

Las pruebas de interacción ejecutan los scripts reales del catálogo y de opiniones: expansión, colapso, búsqueda, orden y filtros. También hay una regresión que comprueba que se pueden mostrar más de 24 opiniones publicadas. El entorno de pruebas usa SQLite y correo en memoria: no se envían correos reales.

La revisión visual en navegador real queda pendiente. Verifica en móvil, tablet y escritorio, con al menos seis productos y seis opiniones, modo oscuro, zoom y la preferencia de movimiento reducido activada.

No se ha diagnosticado ni resuelto la advertencia de antivirus reportada en versiones anteriores. Este paquete no constituye una certificación antivirus.
