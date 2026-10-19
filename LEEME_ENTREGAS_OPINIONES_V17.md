# V17 — Entregas pendientes de cobro y opiniones de clientes

## Actualizar

Conserva tu base de datos, credenciales y volumen de archivos. Reemplaza el código y ejecuta desde la raíz del proyecto, con el entorno virtual activo:

```bash
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reinicia el servicio. En Railway, revisa que la migración y la recolección de estáticos del arranque incluido finalicen correctamente. No necesitas variables nuevas. Recarga con Ctrl+F5 si aún aparece la interfaz anterior.

La migración management/0019 añade el estado de entrega pendiente de pago, imágenes finales y el registro de invitaciones/opiniones. No cambia saldos históricos ni revierte cierres anteriores.

## Entregado sin pagar

En la ficha del pedido, dentro de Actualizar producción o entrega, selecciona **Entregado sin pagar**.

- La entrega física queda registrada, pero no se registra un pago nuevo ni se liquida el saldo.
- Se mantienen los abonos existentes. Solo lo ya recibido cuenta en el total liquidado.
- El pedido sigue contando como vendido y por cobrar. Sale de la cola de fabricación porque ya se entregó.
- Se resalta y subraya en las listas, y aparece una alerta con el saldo pendiente en el resumen.
- Puedes filtrar el estado Entregado sin pagar, combinarlo con pago pendiente y verlo en el calendario.
- El cliente recibe el aviso de entrega con su saldo real si tiene correo registrado, mediante el sistema de avisos existente.

Cuando recibas el saldo completo, pulsa **Registrar pago y cerrar**, disponible en las listas y en la ficha. Registra un pago por el saldo restante y cierra el pedido como venta entregada. El botón debe utilizarse después de recibir el dinero. Una segunda pulsación no duplica el pago.

Si recibes únicamente una parte, utiliza Nuevo abono. Al registrar el último abono, el pedido ya entregado se cierra automáticamente. El cierre informa al cliente del pago final mediante el sistema de correo existente.

La opción anterior **Entregado** conserva el cierre y la liquidación automática solicitados en versiones anteriores. Para conservar una deuda, elige expresamente **Entregado sin pagar**.

## Referencia y producto final

En cada ficha hay una sección **Referencias, resultados y opiniones**. Si el pedido tiene varios productos, cada línea tiene su propia carga de imágenes. Si es un trabajo sencillo, las imágenes pertenecen al pedido.

Pulsa Cargar o cambiar imágenes para guardar la referencia y una foto del producto final. Se mantienen privadas. Los archivos existentes y los enviados originalmente por el cliente siguen disponibles en sus secciones anteriores.

## Preparar la invitación de opinión

1. Entrega el pedido, con pago completo o pendiente.
2. En la ficha, pulsa Preparar opinión del producto. Si hay varios productos, puedes preparar una invitación para cada uno.
3. Selecciona un producto del inventario o escribe un título manual. Este título lo define gestión; el cliente no lo modifica.
4. Revisa las copias de la referencia y del resultado final. Ambas imágenes son necesarias para habilitar el formulario.
5. Guarda la invitación. Copia su URL y compártela con el cliente por el medio que prefieras.

Preparar de nuevo la opinión del mismo producto recupera la invitación existente. Generar otra URL invalida la anterior; Revocar enlace deshabilita el formulario. No se envían invitaciones por correo automáticamente al preparar una opinión.

## Lo que ve el cliente

El enlace muestra el título, las unidades, la referencia y el producto final, sin datos de pago ni contacto del pedido. El cliente escribe su nombre completo y elige de una a cinco estrellas. El comentario es opcional.

La fecha se registra automáticamente. Se solicita autorización para publicar su nombre, calificación, texto e imágenes. Cada invitación admite una sola respuesta. Las validaciones conservan los datos escritos y el formulario utiliza protección CSRF.

## Publicar en la página

En Gestión > Opiniones puedes filtrar invitaciones pendientes, respuestas recibidas y opiniones publicadas. Abre una respuesta, revísala y pulsa **Publicar opinión**. Puedes ocultarla después.

El nombre, las estrellas y el comentario del cliente no se editan desde gestión. El producto, sus imágenes y el título se preparan antes de que responda, para conservar lo que calificó.

La página muestra **Lo que piensan nuestros clientes**, con referencia/resultado, estrellas, nombre, fecha, comentario si existe, promedio y número de calificaciones. Se muestran las últimas 24 opiniones publicadas; el promedio contempla todas las publicadas. El diseño usa los colores de VillaTech, tarjetas adaptables y animaciones que respetan la preferencia de movimiento reducido.

Si no hay ninguna calificación publicada y autorizada, se omite toda la sección. Tampoco se cargan sus estilos y animaciones en la página principal. No se generan opiniones de ejemplo.

Al eliminar un pedido se eliminan también sus invitaciones/opiniones y se programan para limpieza las imágenes que le pertenecen, incluidas las copias públicas. No se eliminan imágenes del catálogo ni archivos originales del cliente.

## Verificación

Se comprobaron el flujo financiero anterior y el nuevo, la protección frente a cobros duplicados, los abonos parciales, el calendario, el acceso privado a imágenes, las opiniones por producto, las validaciones, la protección CSRF en HTTPS, la publicación/ocultamiento y la limpieza al eliminar pedidos. Las pruebas usan correo en memoria, sin envíos reales.

No se verificó el diseño en un navegador gráfico en este entorno. Tras desplegar, prueba el formulario en un móvil y un computador, y revisa la sección pública después de publicar tu primera calificación real.
