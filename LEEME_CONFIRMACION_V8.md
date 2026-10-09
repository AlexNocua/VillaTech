# VillaTech: confirmación de cotizaciones — V8

## Corrección
La captura recibida muestra un rechazo CSRF (403), antes de ejecutar la aprobación. La configuración anterior confiaba en los orígenes indicados por variables y Railway; no añadía automáticamente el dominio público. El ejemplo usaba el dominio sin www y el enlace reportado usa www. No se puede determinar el motivo exacto del rechazo sin el registro del servidor.

Ahora se añade el origen configurado en PUBLIC_SITE_URL y, cuando este corresponde al dominio de VillaTech por HTTPS, se permiten explícitamente https://villatechubate.com y https://www.villatechubate.com. No se permiten comodines ni orígenes enviados por el visitante. Se mantienen el token CSRF y las cookies seguras.

La página solicita una cookie CSRF, evita caché y limita el Referer al mismo origen (corregido en V10). GET solo muestra la cotización; POST con aceptación y CSRF válido confirma una sola vez. Si el formulario caduca o se bloquean cookies, aparece una página de VillaTech con un enlace para obtener un formulario nuevo, sin repetir el envío automáticamente.

## Vista pública
Logo original, resumen de productos y cantidades, total COP, vigencia en hora de Colombia y aceptación explícita. Tras confirmar: estado actual, entrega estimada, abonos y saldo pendiente. Diseño adaptable a teléfonos. No se modifica la página principal ni sus toast ni las credenciales de correo.

## Actualización del alojamiento
1. Despliega este proyecto y ejecuta collectstatic según el inicio habitual del servicio. No hay migraciones nuevas respecto a V7.
2. Conserva tus credenciales, SECRET_KEY, base de datos y variables existentes. PUBLIC_SITE_URL debe ser la URL pública real; se recomienda https://www.villatechubate.com. Las configuraciones existentes con https://villatechubate.com también están contempladas.
3. Railway ya activa la lectura del encabezado HTTPS de su proxy. En otro alojamiento con un proxy confiable que envía X-Forwarded-Proto, establece TRUST_PROXY_HEADERS=true únicamente si el backend solo se puede alcanzar a través de ese proxy.
4. Abre el enlace de una cotización vigente en el navegador, revisa y confirma. Un enlace vencido requiere renovar y enviar la cotización desde gestión.
5. Si persiste un 403, revisa en los registros django.security.csrf si falla el origen, falta la cookie o no coincide el token. No publiques enlaces de aprobación ni credenciales. Evita reglas del CDN que fuercen caché para /gestion/confirmar-cotizacion/.

No se ha desplegado esta versión en el servidor. No se ha confirmado el pedido real del enlace compartido.
