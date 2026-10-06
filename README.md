# Landing page de VillaTech para Django

Landing page modular creada con Django Template Language (DTL), CSS nativo y Anime.js 4.5.0. Está orientada a los servicios de impresión 3D, diseño y prototipado, y desarrollo de soluciones digitales de VillaTech.

## Estructura

~~~text
villatech_landing_django/
├── templates/
│   └── landing/
│       ├── base.html
│       ├── pages/
│       │   └── landing.html
│       └── components/
│           ├── brand.html
│           ├── navbar.html
│           ├── scroll-story.html
│           ├── hero.html
│           ├── services.html
│           ├── print-lab.html
│           ├── bridge.html
│           ├── process.html
│           ├── showcase.html
│           ├── catalog.html
│           ├── faq.html
│           ├── contact.html
│           ├── cookie-consent.html
│           └── footer.html
└── static/
    └── landing/
        ├── css/
        │   ├── tokens.css
        │   ├── globals.css
        │   └── components/
        ├── icons/
        │   └── sprite.svg
        ├── images/
        │   ├── villatech-logo-256.webp
        │   └── villatech-logo-512.webp
        ├── js/
        │   ├── animations.js
        │   ├── scroll-story.js
        │   ├── catalog.js
        │   ├── cookie-consent.js
        │   ├── theme-bootstrap.js
        │   ├── theme.js
        │   └── navigation.js
        └── vendor/
            └── animejs/
                ├── anime.esm.min.js
                └── LICENSE.md
~~~

## Integración rápida

1. Copia `templates/landing` dentro del directorio de plantillas de tu proyecto.
2. Copia `static/landing` dentro del directorio de archivos estáticos.
3. Verifica que `django.contrib.staticfiles` esté habilitado y que Django encuentre ambos directorios.
4. Renderiza `landing/pages/landing.html` desde tu vista.

Ejemplo mínimo de vista:

~~~python
from django.shortcuts import render


def landing(request):
    return render(
        request,
        "landing/pages/landing.html",
        {
            "site_name": "VillaTech",
            "site_email": "contacto@tudominio.com",
            "whatsapp_url": "https://wa.me/57XXXXXXXXXX",
            "contact_form_action": "/contacto/",
        },
    )
~~~

Ejemplo de URL:

~~~python
from django.urls import path
from .views import landing

urlpatterns = [
    path("", landing, name="landing"),
]
~~~

## Variables de contexto opcionales

| Variable | Uso |
| --- | --- |
| `site_name` | Nombre mostrado en la marca y los metadatos. |
| `site_email` | Correo visible en contacto y pie de página. |
| `whatsapp_url` | Enlace completo de WhatsApp para las llamadas a la acción. |
| `contact_form_action` | Endpoint que procesará el formulario de contacto. |
| `canonical_url` | URL canónica para SEO. |
| `social_image_url` | Imagen para Open Graph y redes sociales. |
| `brand_logo_url` | URL alternativa para el logo. Si no se envía, se usa el sello oficial optimizado incluido. |
| `projects` | Lista opcional de proyectos para sustituir los tres casos de muestra. |
| `catalog_products` | Productos que reemplazan las seis referencias iniciales del catálogo. |

Cada elemento de `projects` puede incluir `category`, `title`, `description` y `tags`.

## Logo oficial

El sello de VillaTech está incluido en WebP a 256 px y 512 px. La variante pequeña pesa menos de 8 KB y se precarga para la navegación; las apariciones ubicadas debajo del primer pantallazo usan carga diferida. `brand_logo_url` sigue disponible si más adelante el logo se sirve desde un modelo o almacenamiento propio.

## Catálogo conectado a Jinja

Sin `catalog_products`, la plantilla muestra seis referencias de demostración en llaveros, productos técnicos y figuras. La búsqueda, los filtros, el orden y la transferencia del nombre del producto al formulario funcionan sin backend ni peticiones de red.

La vista puede sustituir las referencias con una lista o `QuerySet` preparado para plantilla:

~~~python
catalog_products = [
    {
        "slug": "llavero-iniciales",
        "name": "Llavero con iniciales",
        "category_slug": "llaveros",  # llaveros, tecnicos o figuras
        "category_label": "Llaveros",
        "description": "Descripción breve y verificable.",
        "price_display": "Cotización según cantidad",
        "image_url": "/media/catalogo/llavero.webp",
        "is_available": True,
        "is_featured": True,
        "tags": ["PLA", "Personalizable"],
    }
]
~~~

No se usa `|safe`: Django mantiene el autoescape de nombres, textos, etiquetas y URL. Conserva esa regla al conectar el modelo. Si incorporas categorías nuevas, añade un botón con `data-catalog-filter` y usa exactamente el mismo slug en `category_slug`.

## Tema claro y oscuro

El tema se selecciona en este orden:

1. Preferencia guardada en `localStorage`.
2. Preferencia del sistema operativo.
3. Tema claro como respaldo.

El botón de la barra de navegación permite alternarlo y conserva la selección. Todos los colores principales se administran desde `static/landing/css/tokens.css`.

## Animaciones de impresión 3D

La landing incluye Anime.js 4.5.0 como módulo ES local, por lo que las animaciones no dependen de una CDN ni requieren un proceso de compilación.
El módulo se carga desde `landing/base.html`, de modo que no depende de que una página hija recuerde declarar un bloque JavaScript adicional. Cuando termina de inicializarse, el elemento `<html>` queda marcado con `data-animations="ready"` para facilitar el diagnóstico desde las herramientas del navegador. Si una escena aislada falla, las demás continúan y el valor cambia a `partial`, acompañado por `data-animation-failures`.

Las escenas implementadas son:

- Entrada escalonada del contenido principal.
- Narrativa central persistente con ocho etapas: idea, diseño, impresión, conexión, desarrollo, solución, claridad y lanzamiento.
- Panel visual protagonista que alterna entre izquierda y derecha, cambia de escala y termina ampliado en el centro; el contenido ocupa siempre el lado opuesto en escritorio.
- Ficha técnica animada por etapa con contexto y métricas específicas de CAD, material, altura de capa, cautín, backend, validación y entrega.
- Cierre independiente antes del formulario: la escena de lanzamiento termina y se oculta al entrar en contacto para no cubrir ningún campo.
- Pausa visual durante el catálogo para que las tarjetas ocupen todo el ancho; el modo “Ver solo animación” continúa disponible.
- Botón “Ver solo animación” que oculta el contenido visual de la página, centra el panel y conserva el recorrido de sus ocho escenas mediante scroll; `Esc` restaura la interfaz.
- Fondo técnico con rejillas, señales, órbitas y líneas SVG que cambian de significado al recorrer la página.
- Simulación de un cautín recorriendo pistas electrónicas, trazando el circuito y generando destellos.
- Transformación visual del circuito en una ventana de código con terminal animada y texto tipo compilación.
- Títulos divididos por palabras que desaparecen al abandonar una sección y reaparecen al regresar.
- Repetición automática de las escenas tanto al bajar como al volver a subir por la página.
- Cabezal que recorre la geometría de la pieza mediante `svg.createMotionPath()`.
- Trazado progresivo de capas con `svg.createDrawable()`.
- Timeline continuo del visor 3D con contador de capas y progreso.
- Laboratorio de impresión activado al entrar en pantalla mediante `onScroll()`.
- Construcción de una pieza en doce capas con `stagger()`.
- Movimiento del cabezal, ascenso del eje y giro del filamento sincronizados.
- Botón para repetir manualmente la impresión.
- Aparición progresiva de servicios, proceso, proyectos y productos del catálogo.

Las animaciones se pausan cuando la pestaña queda oculta y se sustituyen por su estado final cuando el dispositivo tiene activa la preferencia `prefers-reduced-motion: reduce`. La narrativa central expone `data-story-animations="ready"` en `<html>` cuando termina de inicializarse.

Al abrir la página, el terminal de Django debe registrar también estas solicitudes:

~~~text
GET /static/landing/css/components/print-lab.css
GET /static/landing/css/components/scroll-story.css
GET /static/landing/js/animations.js
GET /static/landing/js/scroll-story.js
GET /static/landing/vendor/animejs/anime.esm.min.js
~~~

Si no aparecen, la vista está renderizando una versión anterior de `landing/pages/landing.html` o existe otra plantilla con el mismo nombre antes en el orden de búsqueda de Django.

Para confirmar qué archivos está encontrando Django:

~~~powershell
python manage.py findstatic landing/js/animations.js --verbosity 2
python manage.py findstatic landing/js/scroll-story.js --verbosity 2
python manage.py findstatic landing/css/components/print-lab.css --verbosity 2
python manage.py shell -c "from django.template.loader import get_template; print(get_template('landing/pages/landing.html').origin)"
~~~

Después de reemplazar los archivos, reinicia `runserver` y fuerza una recarga completa en Chrome con `Ctrl + F5`. En la consola del navegador, `document.documentElement.dataset.animations` y `document.documentElement.dataset.storyAnimations` deben devolver `ready`.

Documentación oficial utilizada: [Anime.js](https://animejs.com/documentation/) y [guía de instalación](https://animejs.com/documentation/getting-started/installation).

## Formulario

La plantilla incluye `{% csrf_token %}`, consentimiento obligatorio y validación HTML. La recepción, validación servidor, limitación de frecuencia, almacenamiento o envío de los datos debe implementarse en la vista indicada mediante `contact_form_action`. Nunca confíes únicamente en la validación del navegador.

## Privacidad, cookies y textos legales

El pie abre avisos de privacidad, almacenamiento y términos sin abandonar la página. El gestor registra en `localStorage` únicamente la versión de consentimiento y las categorías elegidas; no se instala analítica ni marketing. Si después conectas una herramienta opcional, espera al evento `villatech:consentchange` y comprueba `event.detail.analytics` o `event.detail.marketing` antes de cargarla.

Los textos son una base editable, no una certificación legal. Antes de producción completa razón social, identificación, dirección, correo de privacidad, plazos, encargados o proveedores y procedimiento de consultas o reclamos según el tratamiento real.

## Rendimiento

- Anime.js se sirve localmente y no depende de una CDN.
- El logo se entrega en WebP con `srcset`, tamaño explícito y decodificación asíncrona.
- Las imágenes futuras del catálogo ya usan dimensiones, `loading="lazy"` y `decoding="async"`.
- Las tarjetas fuera de pantalla usan `content-visibility: auto`.
- El script inicial de tema vive en un archivo externo para facilitar una política CSP sin JavaScript inline.
- En producción usa nombres versionados para estáticos, compresión Brotli/Gzip y caché larga para archivos con hash.

Consulta [SECURITY.md](SECURITY.md) antes de conectar formulario, medios o catálogo al backend.
