(()=>{'use strict';const canvas=document.getElementById('model-canvas');if(!canvas)return;
const status=document.getElementById('model-status'),title=document.getElementById('model-title'),download=document.getElementById('model-download'),zoom=document.getElementById('model-zoom');
const gl=canvas.getContext('webgl',{antialias:true});let generation=0,controller=null,count=0,rx=-.6,ry=.6,scale=1,program,buffer;
function failure(message){status.textContent=message;}
if(gl){try{
 const vs='attribute vec3 p;attribute vec3 n;uniform vec2 angle;uniform float zoom;uniform float aspect;varying vec3 normal;vec3 rot(vec3 v){float a=angle.x,b=angle.y;v=vec3(v.x,cos(a)*v.y-sin(a)*v.z,sin(a)*v.y+cos(a)*v.z);return vec3(cos(b)*v.x+sin(b)*v.z,v.y,-sin(b)*v.x+cos(b)*v.z);}void main(){vec3 v=rot(p);normal=rot(n);gl_Position=vec4(v.x*zoom/aspect,v.y*zoom,v.z*.2,1.0);}';
 const fs='precision mediump float;varying vec3 normal;void main(){float light=.4+.6*abs(dot(normalize(normal),normalize(vec3(.3,.7,1.0))));gl_FragColor=vec4(vec3(.12,.65,.4)*light,1.0);}';
 const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error('shader');return s;};
 program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('program');
 gl.useProgram(program);buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
 for(const [name,offset] of [['p',0],['n',12]]){const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,24,offset);}
 gl.enable(gl.DEPTH_TEST);gl.clearColor(.94,.97,.95,1);
}catch(error){failure('No se pudo iniciar la vista 3D. Puedes descargar el original.');program=null;}}
function draw(){if(!program)return;const rect=canvas.getBoundingClientRect(),ratio=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.max(1,Math.round(rect.width*ratio));canvas.height=Math.max(1,Math.round(rect.height*ratio));gl.viewport(0,0,canvas.width,canvas.height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniform2f(gl.getUniformLocation(program,'angle'),rx,ry);gl.uniform1f(gl.getUniformLocation(program,'zoom'),scale);gl.uniform1f(gl.getUniformLocation(program,'aspect'),canvas.width/canvas.height);gl.drawArrays(gl.TRIANGLES,0,count);}
function reset(){rx=-.6;ry=.6;scale=1;zoom.value=1;draw();}
function setMesh(data){const [lo,hi]=data.bounds,center=lo.map((x,i)=>(x+hi[i])/2),extent=Math.max(...hi.map((x,i)=>x-lo[i]))||1;
 const vertices=[];for(const triangle of data.triangles){const [a,b,c]=triangle,u=b.map((x,i)=>x-a[i]),v=c.map((x,i)=>x-a[i]);let n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],length=Math.hypot(...n)||1;n=n.map(x=>x/length);for(const p of triangle)vertices.push(...p.map((x,i)=>(x-center[i])/extent*1.2),...n);}
 gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);count=vertices.length/6;reset();
 const dims=hi.map((x,i)=>(x-lo[i]).toFixed(2));status.textContent=dims.join(' × ')+' '+data.unit+' · '+data.count.toLocaleString('es-CO')+' triángulos'+(data.shown<data.count?' · vista simplificada ('+data.shown.toLocaleString('es-CO')+')':'');}
for(const button of document.querySelectorAll('[data-preview]'))button.addEventListener('click',async()=>{
 const id=++generation;if(controller)controller.abort();controller=new AbortController();count=0;draw();title.textContent=button.dataset.name;download.href=button.dataset.download;download.hidden=false;
 document.querySelectorAll('[data-preview]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
 if(!program){failure('Este navegador no dispone de vista 3D WebGL. Puedes descargar el archivo.');return;}failure('Preparando geometría…');
 try{const response=await fetch(button.dataset.preview,{credentials:'same-origin',signal:controller.signal,headers:{Accept:'application/json'}});if(id!==generation)return;if(response.redirected){failure('Tu sesión terminó. Ingresa nuevamente a gestión.');return;}const data=await response.json();if(id!==generation)return;if(!response.ok){failure(data.error||'No se pudo mostrar el modelo.');return;}setMesh(data);}catch(error){if(error.name!=='AbortError'&&id===generation)failure('No pudimos cargar la vista. Revisa tu conexión o descarga el original.');}
});
let drag=null;canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!drag)return;ry+=(e.clientX-drag[0])*.01;rx+=(e.clientY-drag[1])*.01;drag=[e.clientX,e.clientY];draw();});for(const event of ['pointerup','pointercancel'])canvas.addEventListener(event,()=>{drag=null;});
canvas.addEventListener('wheel',e=>{e.preventDefault();scale=Math.min(3,Math.max(.3,scale*Math.exp(-e.deltaY*.001)));zoom.value=scale;draw();},{passive:false});
canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')ry-=.1;if(e.key==='ArrowRight')ry+=.1;if(e.key==='ArrowUp')rx-=.1;if(e.key==='ArrowDown')rx+=.1;draw();});zoom.addEventListener('input',()=>{scale=Number(zoom.value);draw();});document.getElementById('model-reset').addEventListener('click',reset);window.addEventListener('resize',draw);draw();
})();
