# Corrección V13 — 3MF demasiado grande para vista previa

El aviso provenía del lector: sumaba el tamaño descomprimido de todos los archivos del paquete y rechazaba el total al superar 64 MB. Un 3MF con miniaturas o datos del laminador grandes podía rechazarse aunque su malla fuese manejable. Además, cada archivo XML tenía un límite de 16 MB y se leía completo en memoria.

Ahora se leen únicamente las partes de geometría referenciadas, por bloques de 64 KB. Se ignoran los contenidos de texturas, miniaturas y datos del laminador que no necesita esta vista. No se construye un árbol XML completo; los vértices e índices se guardan en arreglos numéricos compactos. Se mantienen objetos, componentes, transformaciones y la descarga del original.

Límites actualizados: el archivo subido sigue siendo de hasta 100 MB; cada XML de geometría puede tener hasta 512 MB descomprimidos y el total de XML referenciados hasta 1 GB. Los arreglos de geometría comparten un presupuesto de 192 MB. El recorrido admite hasta cinco millones de triángulos; la vista sigue mostrando una selección de hasta 12.000 para mantener fluidez. El límite del paquete completo de 64 MB fue eliminado.

Si un modelo excede esos límites de procesamiento, muestra un mensaje específico y se conserva la descarga. Se siguen rechazando DTD/entidades, referencias inválidas, componentes cíclicos y coordenadas incorrectas. No se extraen archivos del ZIP al disco ni se envían a otro servicio.

## Aplicar
Actualiza el proyecto, reinicia Django/Gunicorn y vuelve a seleccionar el mismo modelo en la biblioteca. No hay migraciones nuevas ni cambios en las variables del correo. No es necesario cargar de nuevo el archivo ya almacenado.

## Verificación
Se comprobaron un paquete con 80 MB de datos adicionales, un XML geométrico mayor de 16 MB con 600.000 triángulos leído por bloques, rechazo de DTD, presupuesto de memoria y las pruebas anteriores de STL, componentes, transformaciones, acceso privado y avisos. El modelo real que generó el mensaje no se ha adjuntado; no se verificó ese archivo concreto en producción. La corrección está lista para desplegar.
