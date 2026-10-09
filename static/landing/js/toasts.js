(function () {
  'use strict';
  window.villaTechToast = function (message, type) {
    const template = document.getElementById('vt-toast-template');
    if (!template) return;
    const types = {success:'Operación exitosa',error:'Ocurrió un problema',warning:'Atención',info:'Información'};
    type = Object.prototype.hasOwnProperty.call(types,type) ? type : 'info';
    let stack = document.querySelector('.vt-toast-stack');
    if (!stack) {
      stack=document.createElement('section');
      stack.className='vt-toast-stack';
      stack.setAttribute('aria-label','Notificaciones del sistema');
      document.body.appendChild(stack);
    }
    const toast=template.content.firstElementChild.cloneNode(true);
    toast.classList.remove('vt-toast--info');
    toast.classList.add('vt-toast--'+type);
    toast.querySelector('.vt-toast__type').textContent=types[type];
    toast.querySelector('.vt-toast__message').textContent=message;
    const error=type==='error';
    toast.setAttribute('role',error?'alert':'status');
    toast.setAttribute('aria-live',error?'assertive':'polite');
    const delay=error?9000:type==='warning'?7500:6500;
    toast.dataset.bsDelay=String(delay);
    stack.appendChild(toast);
    // Same Bootstrap lifecycle as existing server-rendered notifications.
    if(window.bootstrap && window.bootstrap.Toast){
      const instance=window.bootstrap.Toast.getOrCreateInstance(toast,{autohide:true,delay:delay});
      toast.addEventListener('hidden.bs.toast',()=>{instance.dispose();toast.remove();},{once:true});
      instance.show();
    } else {
      let timer;
      const close=()=>{clearTimeout(timer);toast.classList.remove('show');window.setTimeout(()=>toast.remove(),220);};
      toast.classList.add('show');
      toast.querySelector('[data-vt-toast-close]').addEventListener('click',close,{once:true});
      timer=window.setTimeout(close,delay);
    }
    return toast;
  };
})();
