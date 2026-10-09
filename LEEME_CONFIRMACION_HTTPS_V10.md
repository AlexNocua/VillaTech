# VillaTech — corrección de confirmación HTTPS V10

El aviso Actualiza tu confirmación indica un rechazo CSRF, no un vencimiento de la cotización. Las versiones anteriores enviaban Referrer-Policy: no-referrer y la misma política en una etiqueta meta de las páginas de confirmación y reporte. Esa política puede impedir que un formulario HTTPS envíe la información de origen requerida por Django. La recuperación anterior mostraba un aviso, pero no corregía esta causa.

## Ajuste
Se usa same-origin tanto en la cabecera HTTP como en ambas etiquetas meta. La información Referer puede viajar dentro del mismo sitio, pero no a otros orígenes. Se mantienen el token, la cookie CSRF, la validación del dominio y la confirmación exclusivamente por POST. No se acepta Origin: null como origen confiable ni se desactiva la seguridad.

## Aplicar
Actualiza el proyecto y reinicia el servicio Django/Gunicorn para cargar los archivos Python y las plantillas. Si ya instalaste V9, no hay migraciones nuevas para esta corrección. Si aún no aplicaste sus migraciones, ejecuta:

```bash
python backend/manage.py migrate --noinput
```

Dentro de /app/backend el comando equivalente es python manage.py migrate --noinput. No cambies las credenciales Gmail, las variables actuales ni DJ_KEY_SECRET. Conserva la base existente.

Después de desplegar, cierra la página anterior y vuelve a abrir el enlace desde el correo. Puedes utilizar el mismo enlace si su cotización sigue vigente y no fue reemplazada. La vigencia sigue siendo de 48 horas desde la aceptación del envío del correo. Si realmente venció, usa Reenviar con URL nueva desde gestión.

Para comprobarlo con el navegador: la respuesta de la página y su meta referrer deben indicar same-origin. El POST debe incluir la cookie CSRF, el campo csrfmiddlewaretoken y un Origin del sitio o un Referer HTTPS del sitio. Si el proxy o CDN fuerza una política no-referrer, elimina esa sobreescritura de estas rutas y respeta las cabeceras de Django. Si hay otro rechazo, revisa el motivo concreto en django.security.csrf: falta de cookie, token incorrecto, origen inválido o Referer ausente.

## Archivos funcionales corregidos
- backend/apps/management/customer_security.py
- backend/apps/management/commerce.py
- templates/management/customer_quote.html
- templates/management/customer_issue.html

Se conserva todo el flujo de V9: reenvíos con URL nueva, reportes por correo, eliminación de registros, abonos y cierre de la entrega como venta.

## Verificación
97 pruebas aprobadas. Django check y revisión de migraciones pendientes sin errores. Las pruebas reproducen un POST HTTPS con cookie y token válidos, sin Origin ni Referer (rechazado), y el POST con Referer del mismo sitio (aceptado). También verifican el reporte de problemas por HTTPS, las políticas HTTP y meta y el rechazo de un Referer ajeno.

No se ha confirmado el pedido real ni se ha desplegado esta actualización en tu servidor.

Referencia técnica: https://docs.djangoproject.com/en/5.2/ref/csrf/#removing-the-referer-header
