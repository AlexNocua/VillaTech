# Preparación de seguridad para Django

Esta entrega contiene solo plantillas y archivos estáticos. Los controles del navegador mejoran la experiencia, pero la seguridad real debe aplicarse en la vista, el modelo, el almacenamiento y el servidor de producción.

## Formulario y catálogo

- Conserva `{% csrf_token %}` y no marques la vista con `csrf_exempt`.
- Valida y normaliza en Django todos los campos, incluso opciones de `service`, consentimiento, longitud, teléfono y correo. La validación HTML se puede omitir desde un cliente modificado.
- Mantén el autoescape de Django. No uses `|safe` en nombres, descripciones, etiquetas, mensajes ni URL de productos.
- Limita frecuencia por IP o sesión y añade protección antispam. Evita registrar en logs el cuerpo completo del formulario.
- Si envías correos, trata el nombre y el asunto como datos, no como encabezados construidos sin validar.
- Define expiración y eliminación para solicitudes; permite atender acceso, corrección y supresión según la política publicada.

## Ajustes mínimos de producción

Adapta estos valores a los dominios y al proxy reales:

~~~python
DEBUG = False
ALLOWED_HOSTS = ["villatech.example"]
CSRF_TRUSTED_ORIGINS = ["https://villatech.example"]

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_SSL_REDIRECT = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Activa HSTS solo después de comprobar que todo el dominio funciona por HTTPS.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True  # Únicamente si el dominio cumple los requisitos de precarga.
~~~

Ejecuta antes de desplegar:

~~~bash
python manage.py check --deploy
~~~

Configura `SECURE_PROXY_SSL_HEADER` solo cuando controles el proxy y este elimine encabezados enviados por el cliente.

## Política de seguridad de contenido

Envía CSP como encabezado HTTP desde middleware o servidor. Punto de partida para los archivos locales de esta entrega:

~~~text
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'
~~~

Si `brand_logo_url`, `image_url` o `contact_form_action` apuntan a otro origen, añade únicamente ese origen a `img-src` o `form-action`. No abras la directiva a `*`. Aplica además HTTPS, HSTS tras validarlo, `X-Content-Type-Options: nosniff` y una política de permisos ajustada a las funciones reales.

## Imágenes y archivos de productos

- Limita tamaño, dimensiones y cantidad en el servidor.
- Verifica el contenido real con Pillow o equivalente; no confíes en extensión ni `Content-Type` enviados por el cliente.
- Reconvierte imágenes a formatos permitidos, elimina metadatos y genera nombres aleatorios.
- No aceptes SVG, HTML u otros formatos ejecutables de usuarios como imágenes públicas.
- Sirve medios desde almacenamiento u origen separado, sin permisos de ejecución y con `Content-Disposition` apropiado cuando corresponda.
- Para modelos 3D, usa una lista cerrada de extensiones, análisis adicional y descarga como adjunto; nunca los interpretes mediante comandos de shell construidos con datos del usuario.

## Privacidad y proveedores opcionales

El frontend no carga analítica ni marketing. Si agregas proveedores, documenta finalidad, duración y transferencias; bloquéalos hasta que la categoría correspondiente esté autorizada. Revisa la versión del aviso cuando cambie el tratamiento y permite retirar la elección desde “Preferencias”.

## Rendimiento operativo

- Usa `ManifestStaticFilesStorage` o equivalente para archivos con hash y caché inmutable.
- Comprime respuestas y estáticos con Brotli/Gzip.
- Genera WebP/AVIF y miniaturas en el backend, conserva `width` y `height`, y limita imágenes remotas.
- Pagina el catálogo cuando crezca y filtra en servidor; los filtros actuales son intencionalmente frontend para el catálogo inicial.
- Supervisa errores sin almacenar datos personales innecesarios.

Referencias: [seguridad de Django](https://docs.djangoproject.com/en/5.2/topics/security/), [lista de despliegue de Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [encabezados HTTP de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html) y [CSP de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html).
