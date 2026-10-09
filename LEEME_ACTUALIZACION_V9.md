# VillaTech — actualización V9

## Instalar sobre el proyecto existente
Desde la raíz que contiene backend/, templates/ y static/:

```bash
python backend/manage.py migrate --noinput
python backend/manage.py collectstatic --noinput
python backend/manage.py check
```

Si el contenedor inicia dentro de /app/backend, usa python manage.py en lugar de python backend/manage.py. Reinicia el servicio después de actualizar los archivos. Railway conserva el despliegue y las variables actuales; sus pasos habituales de migración y collectstatic deben ejecutar esta versión.

No borres la base de datos existente ni cambies DJ_KEY_SECRET al actualizar. Esa clave firma los enlaces: cambiarla invalida los correos anteriores. Las credenciales Gmail y el correo destinatario siguen tomando sus valores de las variables actuales.

## Vigencia y confirmación por correo
- Se usa la fecha de vencimiento guardada en la cotización como único control de vigencia; la edad de la firma del enlace no provoca otro vencimiento independiente.
- Las 48 horas empiezan cuando el proveedor acepta el correo, no al ponerlo en cola. La aceptación del proveedor no garantiza llegada a la bandeja de entrada; revisa spam si es necesario.
- Un envío fallido no consume esas 48 horas. Al reintentar un envío que aún no fue aceptado, comienza una ventana completa.
- Solo el POST con aceptación explícita y CSRF válido aprueba. Abrir el correo o visitar el enlace no crea un pedido.
- Una cotización realmente vencida después de 48 horas necesita un nuevo enlace. No se extiende automáticamente al visitarla.
- La migración 0016 reconstruye la vigencia de versiones existentes a partir de su correo aceptado y su sent_at, cuando se dispone de ese registro. No modifica cotizaciones ya aprobadas. Los enlaces reemplazados permanecen inválidos.

## Reenviar con otra URL
En Operación comercial, abre una cotización enviada o vencida y elige **Reenviar con URL nueva**. Se genera otro identificador, se invalidan los enlaces anteriores y se prepara otro correo. Las 48 horas comienzan con la aceptación de ese correo. **Reintentar pendiente** usa la misma versión si el proveedor aún no la aceptó; no duplica correos ya enviados ni prolonga su vigencia. Reenviar no aprueba ni registra pagos.

## Comentarios por problemas de confirmación
Las pantallas de enlace inválido, vigencia terminada o fallo CSRF permiten abrir **Reportar problema y solicitar ayuda**. El cliente escribe un comentario y un correo opcional para responder. El reporte queda guardado y se prepara un aviso a CONTACT_NOTIFICATION_EMAIL mediante el mismo proveedor Gmail API. La ficha muestra los comentarios asociados al registro. Si el envío falla, el reporte se conserva y el aviso puede reintentarse desde Correos. Un comentario no aprueba, cancela ni reenvía automáticamente la cotización; el equipo revisa y pulsa Reenviar con URL nueva.

También se pueden reportar problemas con enlaces anteriores. Cuando no es posible identificar la cotización, el aviso indica Enlace no identificado. Se limita el número de reportes por enlace y origen para evitar envíos repetidos. Si un campo es inválido o el reporte no puede guardarse, el comentario ingresado permanece visible.

## Entregado → venta y saldo liquidado
Seleccionar **Entregado** en la ficha convierte el registro de pedido a venta, deja el saldo pendiente en cero y actualiza el total liquidado al importe del trabajo. No genera un abono manual ficticio. Los abonos previos se conservan; la diferencia queda en el campo Saldo liquidado al entregar y en la actividad. El total vendido sigue contando el mismo registro una sola vez. Se envía el aviso de entrega al cliente si tiene correo.

El resumen usa Saldo liquidado para incluir abonos y cierres automáticos. Las ventas directas previas con saldo pendiente siguen admitiendo abonos. La migración no liquida retroactivamente pedidos antiguos: para un pedido que ya figuraba como entregado, vuelve a seleccionar Entregado en su ficha para aplicar el cierre nuevo.

## Eliminar y depurar
- Desde una ficha, elige Revisar eliminación.
- Desde la operación, selecciona registros de la página y pulsa Revisar eliminación; la selección puede abarcar cotizaciones, pedidos y ventas.
- La pantalla previa muestra los registros y exige confirmar la eliminación permanente.
- Se eliminan el registro y sus líneas, abonos, actividad, avisos y archivos propios; sus importes dejan de sumar a ventas y saldos.
- Se conservan el catálogo, los movimientos de inventario y la solicitud original del formulario. Los comentarios del cliente quedan guardados sin vínculo al registro eliminado.
- Solo personal autorizado de gestión puede eliminar. GET no elimina; POST exige CSRF y confirmación.

## Interfaz
Tarjetas por etapa, iconos SVG locales, filtros por entrega, selección para depurar, producción y saldos organizados por ficha. El logo, los toast del formulario principal, la página pública y la configuración de correo se conservan.

## Verificación
94 pruebas de gestión y formulario principal aprobadas. Incluyen vigencia de 48 horas, firma antigua con vigencia vigente, reenvío y reemplazo de URL, envío fallido y reintento, comentarios, CSRF, eliminación individual y por selección, limpieza de archivos y entrega con abonos previos. Django check, revisión de migraciones pendientes y sintaxis JavaScript aprobados. Migraciones ejecutadas en una base temporal de demostración. La revisión visual en navegador no pudo completarse por falta de acceso a la vista local.

Esta entrega no está desplegada en el servidor y no modifica ni elimina datos de producción.
