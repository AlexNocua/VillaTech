# V18 — Opiniones animadas y experiencias de software

## Actualización

Desde la raíz de villatechdev, con el entorno del proyecto activo:

```bash
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reinicia el servicio y recarga con Ctrl+F5. Railway ya incluye los pasos de arranque: revisa sus resultados en el despliegue. No hay variables nuevas ni cambios de credenciales.

La migración **management/0020_software_reviews** incorpora la relación de opiniones con proyectos de desarrollo, la categoría de experiencia y una descripción pública opcional. Conserva las opiniones existentes y su relación con los pedidos. Una opinión pertenece a un pedido o a un proyecto, sin duplicar ambos orígenes.

## Diseño y animación

La sección pública usa los colores del sitio: verde, lima, azul oscuro y superficies que respetan el tema claro u oscuro.

- Cabecera con una escena de mensajes, estrellas y verificación de experiencia.
- Entrada coordinada de textos y tarjetas; estrellas que aparecen en secuencia.
- Promedio animado hasta el valor real registrado. No se generan calificaciones ni comentarios de ejemplo.
- Tarjetas con referencia, resultado, categoría, opinión, autor y fecha.
- Filtros Todas las experiencias, Impresión 3D y Software y desarrollos.
- Botón para pausar la animación decorativa.
- Animación suspendida cuando la escena sale de pantalla o la pestaña queda en segundo plano.
- Movimiento reducido: desactiva la animación y mantiene las opiniones legibles.
- Si no se carga JavaScript, el contenido sigue visible. Si no hay opiniones publicadas, se omite toda la sección.

Se utiliza el módulo local de **Anime.js v4.5.0**, que ya estaba incluido en el proyecto y se usa en las otras animaciones. No se añade otra copia ni una descarga desde CDN. Referencia de la API: https://animejs.com/documentation.

## Opiniones de software y desarrollos

### Desde un proyecto

1. Abre Gestión > Diseño y desarrollo.
2. Crea o edita el proyecto y ponlo en **Finalizado** cuando corresponda.
3. Pulsa **Preparar opinión del desarrollo** en su tarjeta.
4. Revisa el título, la descripción pública y las imágenes. Se puede tomar una copia de la captura más reciente como resultado final; revisa que sea la adecuada.
5. Carga una imagen de referencia o propuesta y la captura final. Ambas son necesarias para habilitar la URL.
6. Guarda la invitación y comparte el enlace.

El cliente ve el título y la descripción pública que preparaste, las capturas y el formulario de nombre, estrellas y comentario opcional. **No se copia automáticamente la descripción interna del proyecto** ni se expone su galería completa. Evita incluir información confidencial en las capturas que elijas.

### Desde un pedido comercial

Si un sitio web o aplicativo está registrado como pedido, prepara la invitación desde su ficha y selecciona **Software / desarrollo** en Tipo de experiencia. Define el título y la descripción pública manualmente. Así también puedes usar el flujo de pedidos para servicios digitales.

## Gestión y publicación

En Gestión > Opiniones puedes filtrar por tipo de experiencia y estado. Las opiniones de productos y software comparten el mismo proceso:

- Una respuesta por enlace.
- Nombre y estrellas obligatorios, comentario opcional y autorización de publicación.
- Revisión por gestión antes de publicar.
- Opción de ocultar una opinión publicada.
- Las respuestas del cliente no se reescriben desde gestión.

La sección pública diferencia **Compra verificada** de **Desarrollo verificado**, según el origen preparado en gestión.

## Comprobación

La suite de Django cubre los flujos anteriores y las invitaciones de proyectos finalizados, la separación entre productos y software, la privacidad de notas/capturas, la publicación y la integridad del origen de cada opinión. También se comprobaron la sintaxis JavaScript y el contador/línea de tiempo con el módulo real de Anime.js.

No se ejecutó una revisión gráfica en navegador en este entorno. Tras desplegar, comprueba la entrada al desplazarte, los filtros, la pausa, el tema oscuro y la versión móvil.

## Aviso previo de Defender

Esta actualización cambia la sección de opiniones y añade soporte de software. No constituye una resolución de la detección anterior de Defender en templates/base.html y templates/landing/base.html, que no se modifican aquí. No se ha realizado un análisis con Microsoft Defender en este entorno.
