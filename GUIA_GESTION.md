# VillaTech · actualización de gestión

## Instalación

Conserva tu configuración de entorno, tu base de datos y los archivos subidos por usuarios. Haz copia de la base antes de actualizar. Reemplaza el código del proyecto, las plantillas y los estáticos con este paquete. Desde backend, con el entorno virtual activado:

```bash
python manage.py migrate
python manage.py check
```

En producción:

```bash
python manage.py collectstatic --noinput
```

Recarga con Ctrl + F5. Las migraciones agregan campos y tablas; no borran los registros existentes. Las ventas anteriores pasan a Vendido y conservan su fecha original como fecha de venta. Categorías iniciales: Llaveros, Técnicos y Figuras; no sobrescriben las existentes.

## Formularios

- Venta: producto vendido, descripción, cliente, categoría, producto de referencia opcional, precio total, filamento y horas. Estado Vendido y fecha de venta automáticos.
- Pedido: datos comerciales, precio, estado de fabricación, consumo, horas, imagen y logo del PDF. Mantiene variantes de referencia y productos detallados con tamaños, precios e imágenes.
- Gasto: únicamente motivo, categoría y valor. Categorías: filamento, pago mensual, mantenimiento, energía, software/licencias, insumos, servicios y otro.
- Cotización: igual al pedido, sin estado de fabricación. Se genera un PDF con logo blanco o negro sin contar el registro como venta.

## Cotizar antes de vender

En /gestion/registro/quote/ guarda y genera el PDF. Confirmar como pedido transforma el mismo registro en pedido; Registrar como vendido lo transforma en venta. Esto evita duplicar el ingreso y conserva productos, referencias y el PDF. La fecha de venta se registra cuando se marca vendido. No se puede convertir un pedido cancelado; las transiciones son POST y están protegidas por CSRF.

El precio total de una cotización con productos se obtiene de cantidad × precio unitario. Para una cotización sin detalle, se usa el importe del formulario. Si ese importe se deja vacío y se seleccionó un producto de referencia, se toma su precio. Cuando se usa una variante, las medidas/precio manuales tienen prioridad sobre sus valores de referencia.

## Cálculo opcional

Abre Calcular un precio orientativo en el formulario de cotización o pedido. Es un formulario independiente: no es obligatorio para guardar. Calcular muestra el costo/precio por unidad sin cambiar la cotización. Aplicar copia el precio al primer producto; podrás modificarlo. Filamento y horas se multiplican por la cantidad de ese primer producto; si hay otros productos revisa los consumos totales. El cálculo y los valores internos no aparecen en el PDF del cliente.

Las cotizaciones y pedidos no cuentan como ingresos ni gastos. El balance del resumen es ventas menos gastos; no es un reporte contable de utilidad. El filamento agregado excluye cotizaciones y gastos. Formato de cifras: 1.234.567,89.

## Diseño y desarrollo

/gestion/desarrollo/: registra diseño digital, desarrollo web, móvil, software a medida y automatizaciones. Incluye nombre, alcance, cliente, estado, fecha de inicio y capturas. Las imágenes se agregan al editar, hasta 6 por envío y 5 MB cada una, con verificación de contenido. Los proyectos y sus imágenes son privados para usuarios activos del personal. No se publican automáticamente en la landing.

No se crean proyectos de ejemplo en tu base. Debes registrar tus aplicativos actuales.

## Validación

23 pruebas realizadas y aprobadas (22 en la suite y una adicional del límite monetario), revisión de migraciones sin cambios pendientes, sintaxis JavaScript y PDF renderizado revisado visualmente. Se comprueban separación de formularios, estado automático, transición sin duplicación, CSRF, cálculo opcional, formato de cifras y capturas privadas. La revisión visual de la web en un navegador sigue pendiente en este entorno.
