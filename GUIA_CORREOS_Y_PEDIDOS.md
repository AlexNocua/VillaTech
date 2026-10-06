# VillaTech: solicitudes web, correos y cotizaciones

## Qué cambia

Cada envío válido del formulario guarda la solicitud y sus archivos, crea UNA cotización en borrador con origen Página web y registra dos mensajes independientes: confirmación al interesado y aviso al equipo. Las solicitudes históricas guardadas en Contact también se importan como borradores al aplicar la migración, sin enviar correos antiguos.

Gestión → Pedidos y solicitudes web: muestra pedidos y borradores web; permite filtrar estado, origen y buscar cliente/correo/proyecto. Gestión → Cotizaciones: lista los borradores y cotizaciones; mantiene el botón Nueva cotización. Ambas listas tienen paginación de 25 registros.

Revisar → Preparar cotización: conserva el mensaje, contacto y referencias; completa productos, medidas y precios, guarda y genera el PDF. Guardar pasa el borrador a Cotizado. Confirmar como pedido cambia el MISMO registro a Pedido/Pendiente; posteriormente puedes cambiar su estado y registrarlo como vendido. No suma ingresos mientras sea cotización o pedido. Los borradores no se pueden confirmar ni exportar como PDF hasta completar la cotización.

Los adjuntos originales se descargan desde la ficha con acceso exclusivo del personal. No se adjuntan al correo ni se publican mediante enlaces media abiertos. El aviso al equipo enlaza la ficha privada, donde debe iniciar sesión.

## Activar el correo en Railway

Railway Free, Trial y Hobby bloquean SMTP. Usa Resend por HTTPS en estos planes; el proyecto tiene ese transporte configurado por defecto en Railway. En Pro o superior puedes elegir SMTP. Referencia: https://docs.railway.com/networking/outbound-networking

### Opción HTTPS: Resend

1. Crea una cuenta en https://resend.com y verifica un dominio de envío con los registros que ese proveedor indique. La verificación del dominio para correo es distinta del TXT de Railway. Resuelve primero la retención del dominio con Conexcol si sigue activa.
2. Crea una API key con permiso de envío.
3. En Variables del servicio Django agrega:

```dotenv
EMAIL_PROVIDER=resend
RESEND_API_KEY=TU_API_KEY
DEFAULT_FROM_EMAIL=VillaTech <notificaciones@villatechubate.com>
CONTACT_NOTIFICATION_EMAIL=villatechingenieria@gmail.com
PUBLIC_SITE_URL=https://villatechubate.com
EMAIL_TIMEOUT=10
```

DEFAULT_FROM_EMAIL debe ser un remitente permitido por el dominio verificado en Resend; no basta poner una dirección Gmail arbitraria. Si tu dominio aún no está disponible, PUBLIC_SITE_URL puede ser la URL pública real que Railway generó para tu servicio. No uses el dominio railway.internal. En modo de prueba de Resend, los destinatarios pueden estar restringidos; verifica tu dominio para enviar a clientes reales.

CONTACT_NOTIFICATION_EMAIL define el destinatario del aviso. Si lo omites, utiliza EMAIL_HOST_USER, cuando esté configurado. Con Resend conviene definir CONTACT_NOTIFICATION_EMAIL explícitamente.

### Opción SMTP: Railway Pro o superior

```dotenv
EMAIL_PROVIDER=smtp
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=villatechingenieria@gmail.com
EMAIL_HOST_PASSWORD=CONTRASENA_DE_APLICACION
DEFAULT_FROM_EMAIL=VillaTech <villatechingenieria@gmail.com>
CONTACT_NOTIFICATION_EMAIL=villatechingenieria@gmail.com
PUBLIC_SITE_URL=https://villatechubate.com
EMAIL_TIMEOUT=10
```

Para Gmail usa una contraseña de aplicación, si tu cuenta lo permite, con verificación en dos pasos activada. No uses la contraseña habitual de la cuenta. Referencia: https://support.google.com/accounts/answer/185833?hl=es

Si tenías EMAIL_BACKEND configurada en Railway, elimina esa variable para que EMAIL_PROVIDER seleccione el transporte; una EMAIL_BACKEND explícita tiene prioridad.

## Actualización y migraciones

Copia los archivos del paquete sobre tu repositorio actual, conservando tus variables y datos. El paquete no contiene .git, entornos virtuales, credenciales ni bases de datos locales. Mantiene la configuración Docker/Railway y las migraciones anteriores.

Incluye y sube las nuevas migraciones:
- landing/0007_contactemail.py
- management/0008_entry_contact_entry_customer_email_and_more.py
- management/0009_import_existing_web_requests.py

El predeploy actual ya ejecuta migrate. Si lo cambiaste en el panel, conserva:

```sh
python manage.py check --deploy && python manage.py migrate --noinput
```

Prueba local desde backend, con tu entorno virtual activado:

```sh
python manage.py migrate --noinput
python manage.py test apps.landing apps.management
python manage.py runserver
```

Para probar el flujo local sin enviar correos reales, configura en tu entorno:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
CONTACT_NOTIFICATION_EMAIL=villatechingenieria@gmail.com
DEFAULT_FROM_EMAIL=VillaTech <pruebas@example.com>
PUBLIC_SITE_URL=http://localhost:8000
```

Esto imprime los mensajes en consola. No lo uses para comprobar entrega real en producción.

## Verificación en producción

1. Envía una solicitud usando un correo que controles.
2. Comprueba la confirmación al interesado y el aviso al destinatario configurado; revisa spam.
3. En Gestión → Pedidos y solicitudes web filtra Página web / Borrador.
4. Abre la ficha, revisa los adjuntos y los dos estados de correo.
5. Prepara la cotización, guarda y confirma como pedido. El ID y el origen se mantienen.
6. Comprueba que el PDF abra y que el registro aparezca al filtrar Pendiente.

El texto de éxito del formulario confirma el registro de la solicitud; no promete entrega del correo. “Aceptado por proveedor” significa que SMTP/Resend aceptó el envío, no que llegó a bandeja de entrada. Para rebotes y entrega consulta los registros del proveedor.

## Fallos y reintentos

Los mensajes se guardan en PostgreSQL antes de enviarse. Un fallo no elimina la solicitud ni su borrador. Cada correo registra estado, número de intentos y tipo de error; no se escriben credenciales en los logs.

Desde la ficha usa Reintentar correos pendientes. También, desde backend dentro del entorno de producción:

```sh
python manage.py retry_contact_emails
```

Los mensajes aceptados se omiten en los reintentos. Resend usa una clave de idempotencia por mensaje (vigencia del proveedor: 24 horas); SMTP no ofrece esa garantía si el proceso se interrumpe justo después de aceptar un correo. No se añadió un worker ni un cron automático: el primer intento se realiza después de guardar la solicitud, y el reintento es manual.

Si el aviso falló por no tener destinatario, configura CONTACT_NOTIFICATION_EMAIL y reintenta: se completará el destinatario faltante. Los destinatarios ya guardados se conservan.

No se envía automáticamente el PDF al cliente: el correo inicial es un acuse de recepción. Puedes descargar la cotización para revisarla y compartirla después.

## Media

Mantén el volumen del servicio Django montado en /data y MEDIA_ROOT=/data/media. PostgreSQL conserva referencias y estados; el volumen conserva archivos. Haz respaldos de ambos.

## Validación realizada

32 pruebas locales aprobadas. Verificación de solicitud, dos correos separados, fallo y reintento, privacidad de adjuntos, filtros, PDF de borrador bloqueado, transición sin duplicación, importación histórica y payload HTTPS simulado. No se realizó un envío real ni un despliegue en tu cuenta: requieren las credenciales y el dominio de envío verificado.
