# Actualización de correos y gestión VillaTech

## Aplicar la actualización

1. Respalda la base de datos y los archivos privados antes de desplegar.
2. Actualiza el código conservando tus variables de Railway, backend/.env, archivos OAuth y almacenamiento. El ZIP de entrega omite credenciales, bases locales y entornos virtuales.
3. Ejecuta desde la raíz `python backend/manage.py migrate --noinput`. En el contenedor Railway, situado en /app/backend: `python manage.py migrate --noinput`. El despliegue web existente ya ejecuta las migraciones.
4. La nueva migración es management 0012. Conserva los registros anteriores sin inventar fechas ni enviar confirmaciones retroactivas. En Pedidos, filtra Sin fecha y programa cada registro existente.
5. Mantén EMAIL_PROVIDER=gmail_api y el backend Gmail actual. No necesitas generar nuevas credenciales para usar las plantillas de correo. Para cambiar de remitente debes autorizar esa cuenta.

## Flujo operativo

Solicitud web → cotización borrador → cotización preparada → pedido confirmado → pendiente / impresión / listo → entregado.

El pedido suma al vendido al confirmarse. Abonos y saldo por cobrar son independientes de producción. Marcar Entregado no registra un pago. Archivar un pedido entregado como venta conserva el mismo registro y no duplica valores. Las ventas directas siguen disponibles en Ventas y saldos.

Cada ficha reúne el documento PDF, aprobación, producción, entrega, abonos y estado de correos. El PDF queda plegado para priorizar las acciones. El catálogo administra existencias; cotizaciones y pedidos solo vinculan referencias. Las salidas de inventario se registran explícitamente: no se descuenta stock automáticamente al entregar trabajos personalizados.

## Fechas y avisos

La fecha sugerida usa una cola única de producción, 8 horas por día hábil y 1 día adicional de acabado. Sin horas registradas, la base son 3 días hábiles. Se respetan las fechas de otros pedidos activos y se excluyen sábados y domingos; no hay calendario de festivos ni distribución por impresora. Revisa siempre la fecha propuesta y ajústala a lo acordado con el cliente.

Confirmar un pedido con correo del cliente crea un aviso con su fecha estimada. Cambiar fecha o estado crea una actualización; entregar o cancelar genera el aviso correspondiente. Si no hay correo, el pedido se guarda y no se crea un envío sin destinatario. Agrega el correo y guarda un cambio de seguimiento para enviar una actualización posterior.

Los avisos se guardan antes del envío. Si falla Gmail, el pedido no se pierde y el error resumido queda en Avisos de pedidos y en los logs. Los correos aceptados se omiten en los reintentos. Si una conexión se interrumpe tras la aceptación, revisa Enviados antes de reintentar: Gmail no garantiza deduplicación con la cabecera usada por la aplicación.

## Activar el resumen diario en Railway

La agenda de gestión funciona inmediatamente después de migrar. El correo diario requiere un segundo servicio Cron; no se activa por desplegar el servicio web.

1. Crea un servicio separado desde el mismo repositorio y rama. No cambies el servicio web existente.
2. En su configuración, selecciona el archivo `deploy/railway-alerts.example.json` como Railway Config File. Usa raíz de proyecto y el mismo Dockerfile. Este archivo no incluye healthcheck ni servidor web.
3. Copia o referencia las variables de conexión a la MISMA base PostgreSQL, configuración Django, correo Gmail y URL pública del servicio web. No uses una SQLite aislada para el Cron.
4. CONTACT_NOTIFICATION_EMAIL define el correo que recibe las alertas. DEFAULT_FROM_EMAIL debe coincidir con la cuenta autorizada. PUBLIC_SITE_URL debe ser la URL HTTPS real de VillaTech.
5. El comando, ejecutado en /app/backend, es `python manage.py send_order_alerts`.
6. La programación `0 13 * * *` corresponde a las 8:00 a. m. en Colombia (UTC-5). Railway usa UTC. Puedes ajustar la hora.
7. Ejecuta Run Now en el servicio Cron para verificar un resumen real si hay pedidos pendientes. Comprueba los logs y la bandeja del destinatario.

El resumen cuenta pendientes, vencidos, entregas de hoy, próximos 3 días calendario y pedidos sin fecha. Se genera como máximo un resumen por fecha local; no envía mensajes diarios cuando no hay pedidos activos. Muestra hasta 100 fechas urgentes y enlaza la agenda completa. El proceso termina después de enviar.

## Reintentos y comprobación

Desde la raíz:

```text
python backend/manage.py check_email_connection
python backend/manage.py retry_contact_emails
python backend/manage.py retry_order_emails
python backend/manage.py send_order_alerts
```

Dentro de /app/backend omite el prefijo backend/. check_email_connection comprueba autorización y conexión sin enviar. Los otros tres comandos pueden enviar correos reales; no pruebes con pedidos o destinatarios ficticios en producción. Enviado significa aceptado por Gmail, no garantiza llegada a la bandeja principal.

## Alcance conservado

Se conserva la página pública, las validaciones y retención de datos y archivos del formulario, el diseño de los toast y las variables existentes. Se reutiliza el logo original `static/landing/images/logo-light-transparent.png` en mensajes MIME inline. El transporte Gmail API permanece igual; no se incluyen claves en la entrega.
