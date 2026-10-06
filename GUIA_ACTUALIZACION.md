# VillaTech · Gestión e impresión 3D

## Instalación en Windows

Haz una copia de seguridad de tu carpeta y de db.sqlite3. El paquete no incluye bases de datos, credenciales ni el entorno virtual. Conserva tu db.sqlite3 en la raíz del proyecto y tu .env en backend; reemplaza los archivos de código y mantén las migraciones anteriores.

Desde la raíz:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
cd backend
python manage.py check
python manage.py migrate
python manage.py setup_categories
python manage.py createsuperuser
python manage.py runserver
```

Si ya tienes un superusuario, puedes utilizarlo. Las cuentas de gestión deben estar activas y tener is_staff; no se permite registro público. Todas las cuentas staff tienen acceso al estudio completo en esta versión básica.

Se verificó con Python 3.12 y Django 5.2.17. El requirements original apuntaba a Django 6.1; se reemplazó por la rama LTS 5.2 verificada. Crea un entorno virtual limpio y ejecuta las pruebas antes de actualizar tu instalación existente.

## Rutas

- `/`: landing, logo claro durante el día y oscuro durante la noche; las animaciones continúan en las demás secciones y no cubren el logo del hero.
- `/gestion/ingresar/`: acceso privado.
- `/gestion/`: resumen.
- `/gestion/registro/sale/`: venta, valor, cliente, imagen y consumo.
- `/gestion/registro/order/`: pedido con estado, precio e imagen; fecha/hora automática de Colombia.
- `/gestion/registro/expense/`: gasto de filamento, pago mensual, mantenimiento u otro. Filamento adquirido y consumido son campos separados.
- `/gestion/producto/`: producto.
- `/gestion/variante/`: tamaño con largo/ancho/alto en cm, imagen y estimación en COP. Puedes cargar varias variantes para un producto.
- `/gestion/calculadora/`: cálculo de material, energía, depreciación, mantenimiento, trabajo y margen.
- `/admin/`: categorías, edición de productos y variantes existente.

En el resumen, pulsa el nombre de un movimiento para editarlo y actualizar el estado del pedido. Los pedidos no generan ventas automáticamente: registra la venta cuando corresponda. El precio del pedido es su total, no un abono. No hay contabilidad fiscal, control de existencias de bobinas ni pagos electrónicos.

Las estimaciones por tamaño son manuales por variante; no se inventa una relación entre volumen y precio. Para calcular utiliza gramos/horas del laminador, soportes y purgas incluidos. El margen es sobre precio final: precio = costo / (1 - margen/100). Valores precargados son ejemplos, no tarifas garantizadas. La reserva por fallos se aplica al costo de producción; evita duplicarla si ya incluiste desperdicio.

## Seguridad incorporada y despliegue

Acceso staff, CSRF, logout por POST, límite de intentos de acceso (10/15 min por IP), límite de solicitudes de contacto, API con permisos de escritura, autoescape y archivos de pedidos/solicitudes privados. Las imágenes verifican contenido real y tamaño (5 MB); referencias de contacto tienen lista de extensiones, máximo 5 y 20 MB total (15 MB por archivo).

No publiques `media/private/`, archivos heredados de contacto, .env ni la base de datos con el servidor de estáticos. La ruta pública de imágenes solo sirve variantes activas vinculadas a productos activos. Archivos de solicitudes 3D/PDF no se ejecutan ni se sirven públicamente; revisión antivirus queda pendiente de integrar.

Configura `IS_PRODUCTION=true`, `DJ_KEY_SECRET`, `DJ_ALLOWED_HOSTS` (dominios separados por coma), `CSRF_TRUSTED_ORIGINS` (orígenes HTTPS) y un certificado TLS. Cookies seguras, HTTPS, HSTS y protección de contenido se activan en producción. Configura Redis mediante `REDIS_URL` para compartir límites entre procesos; el caché local solo cubre un proceso. El servidor web debe limitar el cuerpo de carga a 20 MB y administrar correctamente la IP del cliente detrás de un proxy. No habilites cabeceras de proxy sin controlar ese proxy.

El .env del archivo original contiene configuración privada: conserva tus credenciales fuera del paquete y cambia las que hayan sido compartidas. La clave de desarrollo no debe utilizarse en producción. El envío SMTP no se implementa ni se anuncia como enviado: el formulario confirma solo el guardado de la solicitud. La función anterior era un stub sin envío efectivo.

SQLite se conserva para esta versión básica. Mantén copias de seguridad; para alta concurrencia migra a PostgreSQL. En producción sirve estáticos después de `python manage.py collectstatic` mediante el servidor web.

## Verificación

```powershell
python manage.py test apps.management.tests
python manage.py makemigrations --check --dry-run
python manage.py check --deploy
```

Nueve pruebas: acceso, CSRF, pantallas staff, fecha/usuario automático, API, catálogo/variantes, imagen falsa, cálculo de precios, límites y errores de contacto. Migraciones aplicadas sobre base temporal. La verificación visual con navegador no pudo ejecutarse por un fallo de descarga del navegador; revisar portada y responsive en tu navegador antes del despliegue.

## Archivos principales

`backend/apps/management/`: modelos, formularios, permisos, calculadora y vistas privadas.
`backend/apps/landing/`: variantes, validación y formulario de contacto.
`templates/management/`: interfaz del estudio.
`static/landing/css/management.css`: tema y diseño responsive.
`static/landing/images/logo-light.jpg` / `logo-dark.png`: logos suministrados sin modificar.

Documentación de referencia: https://docs.djangoproject.com/en/5.2/topics/auth/default/


# Versión 2: portada y cotizaciones

Portada centrada: logo arriba, título serif y acciones debajo. Logos con exterior transparente y recorte circular en pantalla; los discos mantienen sus colores originales. Fuentes DejaVu locales con licencia incluida. En pantallas hasta 1179 px, la historia animada se coloca solo antes del formulario, sin fondo superpuesto al resto.

Nuevas rutas:
- /gestion/categorias/: crear/editar categorías; filtros públicos dinámicos.
- /gestion/productos/: biblioteca interna, edición y check Mostrar en la página web. Nuevos productos internos por defecto. La migración conserva la publicación de productos activos anteriores.
- /gestion/impresoras/: perfiles K1C y Creator 5 Pro. Configura costo real, vida útil y mantenimiento.
- /gestion/cotizacion/ID/: visor del PDF privado, generado al guardar el pedido y regenerado al editarlo.

Potencia nominal: K1C 350 W; Creator 5 Pro 1200 W. No son consumos medios constantes. La calculadora permite elegir potencia media medida o potencia nominal conservadora. Introduce las horas y gramos del laminador de cada trabajo. Los perfiles se crean automáticamente con migrate; sus costos de adquisición quedan en cero hasta que los configures.

Los pedidos admiten varias líneas con producto, tamaño, cantidad, precio, imagen de referencia y comparación. Para copiar los datos de una variante, deja medidas/precio vacíos. Los valores e imágenes de referencia se copian al pedido; cotizar nunca publica un producto. Fondo del PDF blanco, logo claro/oscuro elegido en el pedido. Es cotización, no factura.

Actualización desde backend:
```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test apps.management.tests
python manage.py runserver
```

13 pruebas funcionales y PDF renderizado/inspeccionado. Revisión visual de la web en navegador pendiente: el navegador de pruebas no pudo descargarse.

Fuentes nominales oficiales:
https://www.creality.com/es/resources/k1c-page
https://www.flashforge.com/products/flashforge-creator-5-pro

EJEMPLO_COTIZACION.pdf contiene placas ilustrativas con comparación de color, no inventario real de tu negocio. La versión inicial de esta guía describe funciones anteriores; este apartado prevalece donde haya diferencias.


## Actualización v3 — portada, animaciones y energía

- Se elimina el selector que reducía la portada a 46vw. Logo, título y botones centrados en todos los tamaños.
- Escritura de VillaTech y entrada del emblema mediante Anime.js local 4.5.0; se repiten al volver a la portada.
- Laboratorio y escena de impresión comparten una simulación SVG isométrica: 18 capas ilustrativas, perímetro y relleno, boquilla sincronizada, filamento flexible y bobina en movimiento. No representa un G-code real.
- Se pausa fuera de pantalla y se repite al regresar. Se respeta prefers-reduced-motion; en móviles se conserva la escena dedicada anterior al formulario.
- Se cancelan las líneas de texto anteriores al cambiar de sección, evitando que una animación vieja sobrescriba la escena nueva.
- Calculadora: perfil K1C seleccionado y método nominal por defecto; los perfiles cambian costos y parámetros. Potencias ya sembradas: K1C 350 W, Flashforge Creator 5 Pro 1200 W. Se conservan personalizaciones existentes.
- Referencias oficiales consultadas el 5 de octubre de 2026: https://store.creality.com/blogs/all/k1c-vs-k1-vs-k1-se y https://www.flashforge.com/products/flashforge-creator-5-pro . La potencia nominal no equivale a potencia media medida. Algunas fichas regionales de Creator 5 Pro muestran otras potencias: confirmar la placa del equipo; editar en /gestion/impresoras/ cuando corresponda.
- No se inventa una potencia media: se permite introducir una medida propia en el método personalizado. COP/kWh y costos de compra requieren tus datos reales.
- Anime.js: https://animejs.com/documentation/timeline y https://animejs.com/documentation/svg .
- Sin nuevas migraciones. Mantén tu base de datos, entorno y archivos de usuarios. Reemplaza templates y static completos; en producción ejecuta collectstatic y recarga la página sin caché.
- Validación: 14 pruebas Django y análisis sintáctico de los módulos JS. La inspección visual en navegador queda pendiente cuando no hay Chromium disponible en el entorno.


## Corrección v4 — SVG y portada

- Corregidas etiquetas SVG autocerradas que quedaron mal formadas en v3; esto podía impedir dibujar la impresora.
- Tamaño intrínseco 560 × 420 y reglas explícitas para evitar colapso dentro de la cuadrícula.
- Logo oficial sin modificaciones adicionales; órbitas decorativas separadas, entrada suave y título escalonado con escritura de la marca.
- Las animaciones se pausan al salir de la portada; el texto permanece completo y legible si se interrumpe la entrada.
- Prueba de regresión que interpreta el SVG como XML y verifica su inclusión en las dos escenas de impresión.
- Reemplazar templates y static completos, incluido printer-scene.html y additive-printer.js. Si el servidor usa estáticos recopilados, ejecutar python manage.py collectstatic --noinput. Recargar sin caché con Ctrl + F5.


## Gestión v6

Consulta GUIA_GESTION.md: esta versión incluye migraciones 0005–0007, formularios separados, cotización previa, cálculo opcional y proyectos de desarrollo. Conserva la base de datos y ejecuta migrate.
