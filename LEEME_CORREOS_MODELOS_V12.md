# VillaTech — correos y biblioteca de modelos V12

## Qué se encontró
Al aprobar una cotización se preparaba la confirmación del cliente, pero no existía un aviso de nuevo pedido para el equipo. Los correos iniciales del formulario estaban en otra cola y no aparecían en la pantalla general de avisos. En backend/.env del adjunto CONTACT_NOTIFICATION_EMAIL estaba vacío y no figuraban configuradas las credenciales Gmail API ni EMAIL_PROVIDER=gmail_api. Esto describe el archivo adjunto, no necesariamente las variables reales de Railway: las variables del servicio tienen prioridad.

## Actualizar
Desde la raíz del proyecto:

```bash
python backend/manage.py migrate --noinput
python backend/manage.py collectstatic --noinput
python backend/manage.py check
python backend/manage.py check_mail_workflow
```

Dentro de /app/backend elimina backend/ del comando. Reinicia el servicio. Se añade management 0017, que crea la biblioteca de modelos independientes. No borres la base ni el volumen de archivos y no cambies DJ_KEY_SECRET ni tus credenciales existentes.

## Configurar y verificar el correo del alojamiento
En el servicio web y también en el servicio de tareas programadas deben estar las variables del mismo proveedor. Para Gmail API, EMAIL_PROVIDER=gmail_api, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET y GMAIL_REFRESH_TOKEN deben tener sus valores autorizados; conserva DEFAULT_FROM_EMAIL y EMAIL_HOST_USER del remitente. CONTACT_NOTIFICATION_EMAIL es el correo que debe recibir tus avisos internos. Si está vacío, se utiliza EMAIL_HOST_USER y, como último respaldo, el correo de DEFAULT_FROM_EMAIL. No pegues credenciales en los logs ni en chats.

check_mail_workflow revisa destinatario y presencia de credenciales sin enviar mensajes ni revelar claves. No comprueba la autorización remota de Google ni garantiza entrega a bandeja. Para una comprobación de transporte real utiliza el comando check_email_connection que ya contiene el proyecto, según su ayuda. No se enviaron correos reales durante esta edición.

## Flujo conservado y ampliado
1. Solicitud nueva en formulario: se guarda la cotización y se preparan dos correos: recibo al cliente y aviso interno de solicitud web.
2. Cotización lista: correo con PDF y enlace de aceptación. Vigencia de 48 horas desde la aceptación del envío por el proveedor. Reenvío con URL nueva disponible en la ficha.
3. Pedido aprobado por enlace, mensaje o gestión: confirmación y entrega estimada al cliente, más un aviso interno de Nuevo pedido confirmado. El aviso al equipo también existe si el cliente no tiene correo.
4. Elaboración, finalización y entrega: se mantienen los avisos del cliente y la liquidación del saldo al entregar, sin crear abonos ficticios.
5. Reportes de problemas y resúmenes de agenda: permanecen en el mismo flujo, con la identidad visual y el logo original.

Los mensajes se guardan antes de intentar enviarlos. Un fallo no elimina la solicitud ni el pedido. El reintento omite los mensajes ya aceptados. El aviso interno de confirmación utiliza una clave única por pedido para impedir duplicados.

## Centro de correos y recuperación
La sección Correos muestra los avisos comerciales y los recibos/avisos de solicitudes del formulario, destinatarios, intentos y motivo seguro del fallo. El botón Reintentar solicitudes y avisos pendientes procesa ambas colas. Enviado significa aceptado por el proveedor, no lectura ni entrega garantizada a bandeja.

Desde el contenedor:

```bash
python manage.py process_email_queue
```

Para recuperar un aviso interno que nunca se generó en la versión anterior para un pedido concreto (reemplaza 12 por el número real):

```bash
python manage.py notify_order_owner 12
```

Este comando no cambia el pedido y no duplica un aviso ya aceptado. No se envían retroactivamente avisos de todos los pedidos antiguos al migrar.

Se incluye deploy/railway-email-queue.example.json para un servicio programado independiente que procese pendientes cada cinco minutos. Debe compartir las variables del correo, la base de datos y el acceso persistente a los archivos/PDF de MEDIA_ROOT. No sustituye el servicio web. Mantén el servicio diario de send_order_alerts si deseas el resumen de agenda; el procesamiento de colas no crea ese resumen por sí solo.

## Biblioteca de modelos
En gestión aparece Modelos STL / 3MF, también accesible desde Inventario. Incluye modelos guardados en productos, adjuntos STL/3MF de clientes y archivos independientes que puedes cargar con nombre y descripción (hasta 100 MB). Los archivos siguen privados y se descargan con sesión de gestión.

Al seleccionar uno se prepara una vista geométrica que puedes girar arrastrando, acercar con la rueda/control y restablecer. El teclado permite girar con las flechas. Se requiere WebGL en el navegador. No usa CDN ni librerías externas. Los archivos originales no se modifican, no se ejecuta GCODE ni se envía el archivo a un servicio externo.

Se admiten STL binarios y de texto. En 3MF se interpretan las mallas, unidades, objetos de construcción, componentes y transformaciones, incluidas piezas referenciadas en otros archivos del paquete. La geometría se presenta con un color uniforme: las texturas, pinturas y ajustes del laminador permanecen en el original, pero no se muestran en esta vista.

La vista se limita a 12.000 triángulos aproximados para mantener fluidez, mostrando el número real de triángulos y las dimensiones. El STL no especifica unidades; se indica unidades del STL. Para 3MF se muestran milímetros. Por seguridad y rendimiento, se limita cada XML a 16 MB, el paquete descomprimido a 64 MB y el recorrido a dos millones de triángulos. Los paquetes no reconocidos, extensiones no compatibles, XML demasiado grande o modelos corruptos muestran un mensaje y conservan la descarga. No sustituye una validación de fabricación en tu laminador.

Referencia del formato: https://github.com/3MFConsortium/spec_core

## Verificación
116 pruebas aprobadas. Django check y revisión de migraciones pendientes sin errores; sintaxis JavaScript verificada. Se probaron parsers STL/3MF, transformaciones y componentes, protección de acceso, cargas/descargas y listado de modelos existentes, aviso al equipo con/sin correo del cliente, fallos y reintentos, diagnóstico sin exposición de credenciales y el resto del flujo previo. La compilación WebGL y la apariencia final no se verificaron en un navegador gráfico de este entorno. No se modificaron datos ni variables del servidor de producción.
