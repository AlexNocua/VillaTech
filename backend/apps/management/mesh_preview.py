"""Bounded geometric preview; original files are never modified."""
import math
import time
import re
import struct
import zipfile
import posixpath
from xml.etree import ElementTree as ET
from pathlib import Path
from array import array
from django.core.exceptions import ValidationError

MAX_FILE=100*1024*1024
MAX_XML=512*1024*1024
MAX_REFERENCED_XML=1024*1024*1024
MAX_GEOMETRY_BYTES=192*1024*1024
MAX_TRIANGLES=5000000
SAMPLE=12000
PREVIEW_SECONDS=8

def check_deadline(deadline):
    if deadline is not None and time.monotonic()>deadline:
        raise ValidationError('El modelo se guardó, pero su geometría requiere más tiempo del disponible para la vista previa. Descarga el original para abrirlo en tu laminador.')


def mesh_preview(field):
    deadline=time.monotonic()+PREVIEW_SECONDS
    if field.size>MAX_FILE:raise ValidationError('El archivo supera el límite de vista previa de 100 MB.')
    with field.open('rb') as file:
        extension=Path(field.name).suffix.lower()
        if extension=='.stl':triangles=stl_triangles(file.read(MAX_FILE+1))
        elif extension=='.3mf':triangles=three_mf_triangles(file,deadline)
        else:raise ValidationError('La vista 3D admite STL y 3MF; puedes descargar los demás formatos.')
        low=[math.inf]*3;high=[-math.inf]*3;sample=[];count=0
        # Deterministic reservoir thinning bounds memory while scanning all bounds.
        stride=1
        for triangle in triangles:
            count+=1
            if count%1024==1:check_deadline(deadline)
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


def three_mf_triangles(file,deadline=None):
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
        if len(infos)>20000:raise ValidationError('El paquete contiene demasiados archivos para esta vista.')
        names={i.filename for i in infos};models={};expansions=0;xml_bytes=0;geometry_budget=[0]
        root_name=next((n for n in names if n.lower()=='3d/3dmodel.model'),None)
        if not root_name:raise ValidationError('No se encontró la geometría principal del 3MF.')
        def load(name):
            nonlocal xml_bytes
            if name not in names:raise ValidationError('Falta una pieza referenciada del 3MF.')
            if name not in models:
                info=archive.getinfo(name)
                if info.file_size>MAX_XML or xml_bytes+info.file_size>MAX_REFERENCED_XML:
                    raise ValidationError('La geometría supera el límite de lectura de esta vista. Descarga el original.')
                xml_bytes+=info.file_size
                with archive.open(name) as stream:
                    root=parse_3mf_xml(stream,geometry_budget,deadline)
                unit=root['unit']
                if unit not in factors:raise ValidationError('Unidad 3MF no reconocida.')
                models[name]=(root,root['objects'],factors[unit])
            return models[name]
        def resolve(element,current):
            path=next((value for key,value in element.items() if key.endswith('}path')),None)
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
            vertices=obj['vertices'];indices=obj['indices']
            for offset in range(0,len(indices),3):
                triangle=indices[offset:offset+3]
                if any(i>=len(vertices)//3 for i in triangle):raise ValidationError('Índice de triángulo no válido.')
                yield [[v*factor for v in transform(vertices[3*i:3*i+3],transforms)] for i in triangle]
            for component in obj['components']:
                yield from expand(resolve(component,name),component['objectid'],[matrix(component.get('transform'))]+transforms,stack+[(name,object_id)])
        for item in root['build']:
            if item.get('printable','1')=='0':continue
            yield from expand(resolve(item,root_name),item['objectid'],[matrix(item.get('transform'))],[])


def parse_3mf_xml(stream,budget,deadline=None):
    """Parse only geometry/build records; ignore text, textures and slicer data.

    Compact numeric arrays replace a full XML tree. The budget is shared by
    every referenced model part so component-heavy archives stay bounded.
    """
    class Target:
        def __init__(self):
            self.stack=[];self.result={'unit':'millimeter','objects':{},'build':[]};self.obj=None;self.root_seen=False
        def doctype(self,*args):raise ValidationError('XML 3MF no permitido: contiene DTD o entidades.')
        def data(self,text):pass
        def start(self,tag,attrs):
            local=tag.rsplit('}',1)[-1];self.stack.append(local)
            if len(self.stack)>64:raise ValidationError('XML 3MF demasiado anidado.')
            if len(self.stack)==1:
                if local!='model':raise ValidationError('No es un documento de modelo 3MF.')
                self.root_seen=True;self.result['unit']=attrs.get('unit','millimeter')
            if self.stack==['model','resources','object']:
                key=attrs['id']
                if key in self.result['objects'] or len(self.result['objects'])>=20000:raise ValidationError('Objetos 3MF duplicados o excesivos.')
                self.obj={'vertices':array('d'),'indices':array('I'),'components':[]}
                self.result['objects'][key]=self.obj
            elif self.obj is not None and self.stack==['model','resources','object','mesh','vertices','vertex']:
                values=[float(attrs[a]) for a in ('x','y','z')]
                if not all(math.isfinite(v) and abs(v)<=1e12 for v in values):raise ValidationError('Coordenadas no válidas.')
                budget[0]+=24
                if budget[0]>MAX_GEOMETRY_BYTES:raise ValidationError('La malla requiere demasiada memoria para esta vista. Descarga el original.')
                self.obj['vertices'].extend(values)
            elif self.obj is not None and self.stack==['model','resources','object','mesh','triangles','triangle']:
                values=[int(attrs[a]) for a in ('v1','v2','v3')]
                if any(v<0 or v>4294967295 for v in values):raise ValidationError('Índice de triángulo no válido.')
                budget[0]+=12
                if budget[0]>MAX_GEOMETRY_BYTES:raise ValidationError('La malla requiere demasiada memoria para esta vista. Descarga el original.')
                self.obj['indices'].extend(values)
            elif self.obj is not None and self.stack==['model','resources','object','components','component']:
                if len(self.obj['components'])>=10000:raise ValidationError('Demasiados componentes.')
                self.obj['components'].append(dict(attrs))
            elif self.stack==['model','build','item']:
                if len(self.result['build'])>=10000:raise ValidationError('Demasiados objetos de construcción.')
                self.result['build'].append(dict(attrs))
        def end(self,tag):
            if self.stack==['model','resources','object']:self.obj=None
            self.stack.pop()
        def close(self):
            if not self.root_seen:raise ValidationError('XML de modelo vacío.')
            return self.result
    parser=ET.XMLParser(target=Target())
    read=0
    while True:
        check_deadline(deadline)
        chunk=stream.read(65536)
        if not chunk:break
        read+=len(chunk)
        if read>MAX_XML:raise ValidationError('Geometría XML demasiado grande para vista previa.')
        parser.feed(chunk)
    return parser.close()


def solid_mesh_preview(field):
    """Write every triangle to a compact seekable binary stream, never thin faces.

    Header: VTM1, uint32 triangle count, six float64 bounds, uint32 mm flag,
    four reserved bytes. Payload: 9 float32 coordinates per triangle (LE).
    The temporary file is owned/closed by the response, including on failure.
    """
    import tempfile
    deadline=time.monotonic()+PREVIEW_SECONDS
    if field.size>MAX_FILE:raise ValidationError('El archivo supera el límite de vista previa de 100 MB.')
    output=tempfile.TemporaryFile(mode='w+b')
    try:
        output.write(b'\0'*64)
        low=[math.inf]*3;high=[-math.inf]*3;count=0
        extension=Path(field.name).suffix.lower()
        with field.open('rb') as file:
            if extension=='.stl':triangles=stl_triangles(file.read(MAX_FILE+1))
            elif extension=='.3mf':triangles=three_mf_triangles(file,deadline)
            else:raise ValidationError('La vista 3D admite STL y 3MF.')
            for triangle in triangles:
                count+=1
                if count%1024==1:check_deadline(deadline)
                if count>MAX_TRIANGLES:raise ValidationError('Modelo demasiado complejo para esta vista sólida. Descarga el original.')
                coordinates=[]
                for point in triangle:
                    for axis,value in enumerate(point):
                        if not math.isfinite(value) or abs(value)>1e12:raise ValidationError('Coordenadas no válidas en el modelo.')
                        low[axis]=min(low[axis],value);high[axis]=max(high[axis],value);coordinates.append(value)
                output.write(struct.pack('<9f',*coordinates))
        if not count:raise ValidationError('No encontramos una malla de triángulos para mostrar.')
        output.seek(0);output.write(struct.pack('<4sI6dI4x',b'VTM1',count,*low,*high,int(extension=='.3mf')));output.seek(0)
        return output
    except Exception:
        output.close();raise
