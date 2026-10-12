"""Bounded geometric preview; original files are never modified."""
import math
import re
import struct
import zipfile
import posixpath
from xml.etree import ElementTree as ET
from pathlib import Path
from django.core.exceptions import ValidationError

MAX_FILE=100*1024*1024
MAX_XML=16*1024*1024
MAX_TRIANGLES=2000000
SAMPLE=12000

def mesh_preview(field):
    if field.size>MAX_FILE:raise ValidationError('El archivo supera el límite de vista previa de 100 MB.')
    with field.open('rb') as file:
        extension=Path(field.name).suffix.lower()
        if extension=='.stl':triangles=stl_triangles(file.read(MAX_FILE+1))
        elif extension=='.3mf':triangles=three_mf_triangles(file)
        else:raise ValidationError('La vista 3D admite STL y 3MF; puedes descargar los demás formatos.')
        low=[math.inf]*3;high=[-math.inf]*3;sample=[];count=0
        # Deterministic reservoir thinning bounds memory while scanning all bounds.
        stride=1
        for triangle in triangles:
            count+=1
            if count>MAX_TRIANGLES:raise ValidationError('Modelo demasiado complejo para esta vista. Descarga el original.')
            for point in triangle:
                for axis,value in enumerate(point):
                    if not math.isfinite(value) or abs(value)>1e12:raise ValidationError('Coordenadas no válidas en el modelo.')
                    low[axis]=min(low[axis],value);high[axis]=max(high[axis],value)
            if (count-1)%stride==0:sample.append(triangle)
            if len(sample)>SAMPLE:
                sample=sample[::2];stride*=2
        if not count:raise ValidationError('No encontramos una malla de triángulos para mostrar.')
        return {'triangles':sample,'count':count,'shown':len(sample),'bounds':[low,high],
                'unit':'mm' if extension=='.3mf' else 'unidades del STL'}


def stl_triangles(data):
    if len(data)>MAX_FILE:raise ValidationError('Archivo demasiado grande.')
    if len(data)>=84:
        count=struct.unpack_from('<I',data,80)[0]
        if count and 84+50*count==len(data):
            if count>MAX_TRIANGLES:raise ValidationError('Demasiados triángulos.')
            for offset in range(84,len(data),50):
                values=struct.unpack_from('<12f',data,offset)
                yield [list(values[3:6]),list(values[6:9]),list(values[9:12])]
            return
    if not data.lstrip().lower().startswith(b'solid'):raise ValidationError('STL no reconocido.')
    number=rb'([-+0-9.eE]+)'
    pattern=rb'\bvertex\s+'+number+rb'\s+'+number+rb'\s+'+number
    group=[]
    for vertex in re.finditer(pattern,data,re.I):
        group.append([float(value) for value in vertex.groups()])
        if len(group)==3:yield group;group=[]
    if group:raise ValidationError('STL incompleto.')


def three_mf_triangles(file):
    factors={'micron':.001,'millimeter':1,'centimeter':10,'inch':25.4,'foot':304.8,'meter':1000}
    identity=[1,0,0,0,1,0,0,0,1,0,0,0]
    def matrix(text):
        result=[float(v) for v in text.split()] if text else identity
        if len(result)!=12 or not all(math.isfinite(v) for v in result):raise ValidationError('Transformación 3MF no válida.')
        return result
    def transform(point,transforms):
        for m in transforms:
            x,y,z=point
            point=[x*m[0]+y*m[3]+z*m[6]+m[9],x*m[1]+y*m[4]+z*m[7]+m[10],x*m[2]+y*m[5]+z*m[8]+m[11]]
        return point
    with zipfile.ZipFile(file) as archive:
        infos=archive.infolist()
        if len(infos)>2000 or sum(i.file_size for i in infos)>64*1024*1024:raise ValidationError('Paquete 3MF demasiado grande para vista previa.')
        names={i.filename for i in infos};models={};expansions=0
        root_name=next((n for n in names if n.lower()=='3d/3dmodel.model'),None)
        if not root_name:raise ValidationError('No se encontró la geometría principal del 3MF.')
        def load(name):
            if name not in names:raise ValidationError('Falta una pieza referenciada del 3MF.')
            if name not in models:
                info=archive.getinfo(name)
                if info.file_size>MAX_XML:raise ValidationError('Geometría XML demasiado grande para vista previa.')
                xml=archive.read(name)
                if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():raise ValidationError('XML 3MF no permitido.')
                root=ET.fromstring(xml)
                unit=root.attrib.get('unit','millimeter')
                if unit not in factors:raise ValidationError('Unidad 3MF no reconocida.')
                objects={o.attrib['id']:o for o in root.findall('./{*}resources/{*}object')}
                models[name]=(root,objects,factors[unit])
            return models[name]
        def resolve(element,current):
            path=next((value for key,value in element.attrib.items() if key.endswith('}path')),None)
            if not path:return current
            result=path.lstrip('/') if path.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(current),path))
            if result.startswith('../') or '\\' in result:raise ValidationError('Referencia 3MF no válida.')
            return result
        root,objects,factor=load(root_name)
        def expand(name,object_id,transforms,stack):
            nonlocal expansions
            expansions+=1
            if expansions>10000 or len(stack)>32 or (name,object_id) in stack:raise ValidationError('Componentes cíclicos o demasiado complejos.')
            part,resources,part_factor=load(name)
            if part_factor!=factor:raise ValidationError('Unidades diferentes entre piezas; descarga el archivo para abrirlo en el laminador.')
            obj=resources.get(object_id)
            if obj is None:raise ValidationError('Objeto 3MF no encontrado.')
            mesh=obj.find('./{*}mesh')
            if mesh is not None:
                vertices=[[float(v.attrib[a]) for a in ('x','y','z')] for v in mesh.findall('./{*}vertices/{*}vertex')]
                for tri in mesh.findall('./{*}triangles/{*}triangle'):
                    indices=[int(tri.attrib[a]) for a in ('v1','v2','v3')]
                    if any(i<0 or i>=len(vertices) for i in indices):raise ValidationError('Índice de triángulo no válido.')
                    yield [[v*factor for v in transform(vertices[i],transforms)] for i in indices]
            for component in obj.findall('./{*}components/{*}component'):
                yield from expand(resolve(component,name),component.attrib['objectid'],[matrix(component.attrib.get('transform'))]+transforms,stack+[(name,object_id)])
        for item in root.findall('./{*}build/{*}item'):
            if item.attrib.get('printable','1')=='0':continue
            yield from expand(resolve(item,root_name),item.attrib['objectid'],[matrix(item.attrib.get('transform'))],[])
