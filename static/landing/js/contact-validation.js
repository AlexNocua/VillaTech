(function () {
  function init() {
    const form = document.querySelector('[data-contact-form]');
    if (!form || !window.fetch) return;
    const feedback = document.querySelector('[data-contact-feedback]');
    const button = form.querySelector('[type="submit"]');
    function notify(message, type) {
      feedback.hidden=false;
      feedback.textContent=message;
      if (window.villaTechToast) window.villaTechToast(message,type || 'error');
      else feedback.classList.remove('sr-only');
    }

    const fields = ['name','phone','email','service','message','privacy_consent','reference_files'];
    form.noValidate = true;
    function show(name, messages) {
      const field = form.elements.namedItem(name);
      const error = form.querySelector('[data-contact-error="'+name+'"]');
      if (error) error.textContent = (messages || []).join(' ');
      if (field) {
        field.setAttribute('aria-invalid', messages && messages.length ? 'true' : 'false');
        if (error) field.setAttribute('aria-describedby', [name==='reference_files'?'contact-files-help':'', error.id].filter(Boolean).join(' '));
      }
    }
    function validate(name) {
      const field = form.elements.namedItem(name), value = field.value.trim();
      let message = '';
      if (name === 'reference_files') {
        const files = Array.from(field.files);
        if (files.length > 5) message = 'Selecciona como máximo 5 archivos.';
        else if (files.reduce((sum,file)=>sum+file.size,0)>20*1024*1024) message = 'Los archivos no pueden superar 20 MB en total.';
        else if (files.some(file=>file.size>15*1024*1024)) message = 'Cada archivo debe pesar máximo 15 MB.';
        else if (files.some(file=>!(/\.(stl|obj|3mf|step|stp|pdf|png|jpe?g|webp)$/i.test(file.name)))) message = 'Formato no permitido. Usa STL, OBJ, 3MF, STEP, STP, PDF, PNG, JPG o WEBP.';
      } else if (name === 'privacy_consent') {
        if (!field.checked) message = 'Acepta el aviso de privacidad para enviar la solicitud.';
      } else if (!value) {
        message = {name:'Escribe tu nombre.',phone:'Escribe tu teléfono.',email:'Escribe tu correo.',service:'Selecciona un servicio.',message:'Describe tu idea.'}[name];
      } else if (name === 'phone' && (!/^\+?[0-9 ()-]{7,25}$/.test(value) || value.replace(/\D/g,'').length<7 || value.replace(/\D/g,'').length>15)) {
        message = 'Introduce un teléfono de 7 a 15 dígitos; puedes usar +57, espacios, paréntesis o guiones.';
      } else if (name === 'email' && (value.length>254 || field.validity.typeMismatch || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))) {
        message = 'Introduce un correo válido, por ejemplo nombre@correo.com.';
      } else if ((name==='name' && value.length>255) || (name==='message' && value.length>500)) {
        message = name==='name' ? 'El nombre debe tener máximo 255 caracteres.' : 'La descripción debe tener máximo 500 caracteres.';
      }
      show(name, message ? [message] : []);
      return !message;
    }
    function focusError(name) {
      const field = form.elements.namedItem(name);
      const target = name==='reference_files' ? form.querySelector('[data-file-dropzone]') : field;
      if (target) { target.scrollIntoView({block:'center',behavior:'smooth'}); if (name==='reference_files') target.tabIndex=0; target.focus({preventScroll:true}); }
    }
    fields.forEach(name=>{
      const field = form.elements.namedItem(name);
      field.addEventListener('blur',()=>validate(name));
      field.addEventListener('input',()=>{ if (field.getAttribute('aria-invalid')==='true') validate(name); });
      field.addEventListener('change',()=>validate(name));
    });
    form.addEventListener('submit', async function(event) {
      event.preventDefault();
      if (button.disabled) return;
      const invalid = fields.filter(name=>!validate(name));
      feedback.hidden=false;
      if (invalid.length) {
        notify('Revisa los campos indicados. Tus datos y archivos siguen aquí.','error');
        focusError(invalid[0]); return;
      }
      button.disabled=true; form.setAttribute('aria-busy','true');
      feedback.textContent='Enviando solicitud…';
      try {
        const response = await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'Accept':'application/json'},credentials:'same-origin'});
        const contentType = response.headers.get('Content-Type') || '';
        if (!contentType.includes('application/json')) {
          notify(response.status===403 ? 'La sesión de seguridad expiró. Copia tus datos antes de actualizar la página e intentar nuevamente.' : 'No pudimos confirmar el envío. Tus datos se conservan. Revisa antes de reintentar para evitar duplicados.','error');
          return;
        }
        const result=await response.json();
        const labels={name:'Nombre',phone:'Teléfono',email:'Correo',service:'Servicio',message:'Descripción',privacy_consent:'Privacidad',reference_files:'Archivos'};
        const details=Object.entries(result.errors || {}).map(([name,errors])=>(labels[name] || name)+': '+errors.join(' ')).join(' ');
        notify([result.message || 'No pudimos confirmar el envío. Tus datos se conservan.',details].filter(Boolean).join(' '),response.ok && result.ok ? 'success' : 'error');
        if (response.ok && result.ok) {
          form.reset(); fields.forEach(name=>show(name,[]));
          const clear=form.querySelector('[data-file-clear]'); if(clear)clear.click();
        } else {
          const errors=result.errors || {};
          Object.entries(errors).forEach(([name,messages])=>show(name,messages));
          const first=fields.find(name=>errors[name]); if(first)focusError(first);
        }
      } catch (error) {
        notify('Se interrumpió la conexión. Tus datos y archivos siguen aquí. No pudimos confirmar si llegó la solicitud; revisa antes de reintentar.','error');
      } finally {
        button.disabled=false; form.removeAttribute('aria-busy');
      }
    });
    const existing=fields.find(name=>form.querySelector('[data-contact-error="'+name+'"]')?.textContent.trim());
    if(existing) {show(existing,[form.querySelector('[data-contact-error="'+existing+'"]').textContent.trim()]);focusError(existing);}
    else if(document.querySelector('[data-vt-toast].vt-toast--error'))form.scrollIntoView({block:'center'});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
