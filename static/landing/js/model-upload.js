/* Upload separately from model geometry; retain entered data on failure. */
(() => {
 'use strict';
 const form=document.querySelector('[data-model-upload]');if(!form)return;
 const file=form.querySelector('input[type=file]'),button=form.querySelector('button[type=submit]');
 const status=form.querySelector('[data-model-upload-status]'),progress=form.querySelector('progress');
 let busy=false;
 file.addEventListener('change',()=>{file.setCustomValidity('');status.textContent='';});
 form.addEventListener('submit',event=>{
  event.preventDefault();if(busy)return;
  const selected=file.files[0];
  file.setCustomValidity(selected && (!/\.(stl|3mf)$/i.test(selected.name)||selected.size>100*1024*1024)?'Selecciona un STL o 3MF de hasta 100 MB.':'');
  if(!form.reportValidity())return;
  const request=new XMLHttpRequest();request.open('POST',form.action||location.href);request.timeout=180000;
  request.setRequestHeader('Accept','text/html');
  busy=true;button.disabled=true;form.setAttribute('aria-busy','true');progress.hidden=false;progress.value=0;
  status.textContent='Enviando modelo… No cierres esta página.';
  request.upload.onprogress=event=>{if(event.lengthComputable){progress.value=event.loaded/event.total*100;status.textContent=event.loaded===event.total?'Archivo enviado. Guardando en la biblioteca…':`Enviando modelo: ${Math.round(progress.value)} %`;}};
  function finish(message){busy=false;button.disabled=false;form.removeAttribute('aria-busy');progress.hidden=true;status.textContent=message;}
  request.onload=()=>{
   if(request.status>=200&&request.status<300){
    const page=new DOMParser().parseFromString(request.responseText,'text/html');
    const returnedForm=page.querySelector('[data-model-upload]');
    if(returnedForm){
     const errors=Array.from(returnedForm.querySelectorAll('.errorlist')).map(node=>node.textContent.trim());
     if(errors.length){finish(errors.join(' '));return;}
     location.assign(request.responseURL);return;
    }
    finish('Tu sesión puede haber terminado. Abre gestión en otra pestaña, inicia sesión y vuelve a intentar.');return;
   }
   finish(request.status===413?'El servidor rechazó el tamaño del archivo. El límite de la biblioteca es 100 MB; revisa también el límite del alojamiento.':request.status===403?'La sesión o el permiso de carga no se pudo verificar. Inicia sesión en otra pestaña y vuelve a intentar.':'El servidor no completó la carga. Revisa la biblioteca antes de reintentar para evitar duplicados. Los datos del formulario se conservaron.');
  };
  request.onerror=()=>finish('La conexión se interrumpió. Revisa si el modelo quedó guardado antes de volver a enviarlo.');
  request.ontimeout=()=>finish('Se agotó el tiempo de espera. Revisa la biblioteca en otra pestaña antes de reintentar: el archivo podría haberse guardado.');
  request.send(new FormData(form));
 });
})();
