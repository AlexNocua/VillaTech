# Flujo unificado de VillaTech

Esta versión reemplaza la navegación separada de cotizaciones y pedidos por **Cotizaciones y pedidos** en `/gestion/flujo/`. El registro conserva su número, productos, documentos, origen web, historial y abonos a lo largo de todo el proceso. Ventas y saldos es una vista financiera de esos registros; no debes duplicar el pedido para cobrarlo.

## Actualización

1. Respalda base de datos y archivos privados. Conserva tus variables y credenciales existentes.
2. Despliega el código. Las migraciones nuevas son management 0013 y 0014. El proceso web existente ejecuta migrate; localmente, desde la raíz, usa `python backend/manage.py migrate --noinput`.
3. Los registros existentes conservan importe, filamento, horas y abonos. En trabajos antiguos se inicializa una unidad con sus valores guardados como base. No se envían correos ni se inventan aprobaciones retroactivas. Revisa las unidades reales antes de editar esos registros.
4. Mantén Gmail API configurada. PUBLIC_SITE_URL debe ser el dominio HTTPS accesible por tus clientes. Conserva estable y privada la clave Django del despliegue: firma los enlaces de aprobación. No necesitas permisos de lectura del buzón.

## Cómo operar

- **Preparar**: crea una cotización sencilla con cliente, descripción, unidades, precio por unidad, filamento por unidad y horas por unidad. Por ejemplo, 2 unidades de 35 g dan 70 g de filamento. Los abonos se registran una vez confirmado el pedido.
- **Detallar productos**: si hay varias piezas, agrega líneas con nombre, descripción, cantidad, precio, filamento y horas por unidad. Los precios de las líneas reemplazan el total sencillo. Si defines consumos en líneas, se suman cantidad × consumo de cada una. Si todas las líneas tienen el consumo en cero, se conserva la base general del trabajo sencillo. El cálculo en pantalla es una vista previa; el servidor vuelve a validar los totales.
- **Enviar**: desde la ficha, pulsa Enviar cotización por correo. Se guarda una copia del mensaje y un PDF con detalle y vigencia. El correo incluye el botón Revisar y confirmar pedido. La vigencia de 48 horas empieza al poner esta versión en la cola de envío; consulta su estado si Gmail falla. Reintentar la misma versión no amplía la vigencia.
- **Confirmar desde el correo**: el cliente abre el enlace, revisa precio y descripción, marca su aceptación y pulsa Confirmar mi pedido. Abrir el enlace por sí solo no aprueba. El mismo registro pasa a pedido Pendiente, suma al vendido y genera el aviso de confirmación con entrega estimada. La aprobación no lo marca como pagado.
- **Confirmar por mensaje o respuesta de correo**: usa la sección Ya recibí la confirmación, selecciona el medio y registra una referencia. Las respuestas del buzón no se leen automáticamente; el botón del correo sí confirma el pedido directamente. Puedes compartir el enlace por WhatsApp desde la ficha.
- **Producir**: actualiza Pendiente → En impresión → Listo → Entregado desde la ficha. Al pasar a elaboración se envía el aviso correspondiente, y al quedar listo se informa que está terminado. También se avisa la entrega, cancelación o cambio de fecha. Guarda solo cuando haya un cambio real para evitar avisos repetidos.
- **Cobrar**: registra abonos antes, durante o después de la elaboración, incluyendo pedidos ya entregados. El saldo es total menos abonos. Un pedido sin pagar sigue contando como vendido. No se permiten abonos que superen el saldo ni cancelar pedidos con abonos sin conciliación.
- **Vencer o renovar**: después de 48 horas sin aceptación, la cotización queda Vencida, fuera del vendido. El enlace deja de aceptar inmediatamente después del límite. Para retomar el trabajo, prepara una nueva versión y vuelve a enviarla. Editar una cotización enviada invalida los enlaces anteriores. Los PDFs ya enviados se conservan como copias independientes.

## Activar vencimiento automático sin visitas

El vencimiento se comprueba al abrir el resumen, la lista unificada, la ficha y cualquier enlace del cliente. La aceptación nunca se permite después del límite, aunque el proceso programado no se haya ejecutado.

Para actualizar el estado en base de datos aun cuando nadie abra el sitio, configura un **servicio Cron separado** desde el mismo repositorio en Railway:

- Railway Config File: `deploy/railway-quote-expiry.example.json`.
- Comando en el contenedor `/app/backend`: `python manage.py process_quote_expiry`.
- Horario: `*/15 * * * *` (cada 15 minutos, UTC).
- Usa las variables Django y la **misma base PostgreSQL** del servicio web. No uses una SQLite independiente ni cambies el proceso del servidor web.
- Primero despliega la web con las migraciones; después activa el Cron. Puedes ejecutar Run Now para comprobar el resultado.

El límite de aprobación es exacto a las 48 horas; el cambio automático de estado puede verse en el siguiente ciclo del Cron. Las cotizaciones preparadas que todavía no se han enviado no vencen. Los pedidos ya aprobados tampoco vencen por esta regla.

El resumen diario de pedidos pendientes de la versión anterior sigue disponible mediante `deploy/railway-alerts.example.json` y `python manage.py send_order_alerts` (servicio separado a las 8 a. m. de Colombia). El Cron de vencimientos y el resumen diario son procesos distintos.

## Envíos fallidos

Todos los avisos guardan su estado. Enviado significa aceptado por Gmail, no confirma lectura ni llegada a la bandeja principal. Reintenta desde la ficha o Correos; las cotizaciones vencidas, aprobadas o sustituidas no vuelven a enviarse. Ante una interrupción de red con resultado incierto, revisa Enviados antes de reintentar.

Desde la raíz del proyecto:

```text
python backend/manage.py check
python backend/manage.py process_quote_expiry
python backend/manage.py retry_contact_emails
python backend/manage.py retry_order_emails
python backend/manage.py send_order_alerts
```

Los tres últimos comandos pueden enviar mensajes reales. Dentro de `/app/backend`, usa `python manage.py ...`.

## Alcance

Se conserva la página pública, los toast, el formulario y las variables existentes. Las rutas anteriores permanecen compatibles con registros y enlaces guardados, pero el flujo principal se opera desde la nueva ficha. Las salidas de inventario siguen siendo explícitas: los trabajos personalizados no descuentan stock automáticamente.

Referencias técnicas: firma de enlaces https://docs.djangoproject.com/en/5.2/topics/signing/ ; confirmación mediante POST https://docs.djangoproject.com/en/5.2/ref/csrf/ ; servicios Cron https://docs.railway.com/cron-jobs .
