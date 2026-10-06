document.getElementById('management-theme')?.addEventListener('click',()=>{const root=document.documentElement;const theme=root.dataset.theme==='dark'?'light':'dark';root.dataset.theme=theme;try{localStorage.setItem('landing-theme',theme)}catch(e){}});
document.getElementById('add-quote-item')?.addEventListener('click',()=>{const count=document.getElementById('id_items-TOTAL_FORMS');if(Number(count.value)>=30)return;const template=document.getElementById('quote-empty');const fragment=template.content.cloneNode(true);fragment.querySelectorAll('[name],[id],[for]').forEach(el=>{for(const attr of ['name','id','for'])if(el.hasAttribute(attr))el.setAttribute(attr,el.getAttribute(attr).replaceAll('__prefix__',count.value));});document.getElementById('quote-items').appendChild(fragment);count.value=Number(count.value)+1;});

const profilesElement=document.getElementById('printer-profiles');
if(profilesElement){
 const profiles=JSON.parse(profilesElement.textContent);
 const select=document.getElementById('id_printer'),mode=document.getElementById('id_energy_mode'),watts=document.getElementById('id_watts');
 function energy(){const profile=profiles.find(p=>String(p.id)===select.value);if(!profile)return;const rated=mode.value==='rated';watts.readOnly=rated;watts.value=rated?profile.rated_watts:(profile.average_watts??'');watts.closest('div').hidden=rated;}
 select.addEventListener('change',()=>{const p=profiles.find(p=>String(p.id)===select.value);if(p)for(const [field,key] of [['printer_price','purchase_price'],['useful_hours','useful_hours'],['maintenance_hour','maintenance_hour']])document.getElementById('id_'+field).value=p[key];energy();});
 mode.addEventListener('change',energy);
 // Keep a submitted measured value after validation errors.
 if(mode.value==='rated')energy();
}

const estimator=document.getElementById('quote-calculator');
if(estimator){
 let estimate=null,inputs=null;
 const feedback=document.getElementById('cost-feedback'),apply=document.getElementById('apply-estimate');
 const cop=value=>new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(Number(value));
 estimator.addEventListener('input',()=>{estimate=null;apply.hidden=true;});
 estimator.addEventListener('submit',async event=>{
  event.preventDefault();const submit=estimator.querySelector('[type="submit"]');submit.disabled=true;apply.hidden=true;estimate=null;
  const data=new FormData(estimator);feedback.textContent='Calculando…';
  try{const response=await fetch(estimator.action,{method:'POST',body:data,credentials:'same-origin',headers:{'X-CSRFToken':data.get('csrfmiddlewaretoken'),'Accept':'application/json'}});const body=await response.json();
   if(!response.ok){feedback.textContent=body.errors?Object.entries(body.errors).map(([label,messages])=>label+': '+messages.join(' ')).join('\n'):'No se pudo calcular. Revisa tu sesión.';return;}
   estimate=body.result;inputs=data;feedback.textContent='Costo por unidad: '+cop(estimate.cost)+' · Precio sugerido: '+cop(estimate.price)+'\nEl resultado es orientativo; puedes ajustar el precio.';apply.hidden=false;
  }catch(error){feedback.textContent='No se pudo calcular. Revisa tu conexión e inténtalo de nuevo.';}
  finally{submit.disabled=false;}
 });
 apply.addEventListener('click',()=>{
  if(!estimate)return;
  const target=document.querySelector('#quote-items [name$="-unit_price"]')||document.getElementById('id_amount');
  if(!target)return;target.value=estimate.price;target.dispatchEvent(new Event('input',{bubbles:true}));
  const quantity=Number(document.querySelector('#quote-items [name$="-quantity"]')?.value||1);
  for(const [field,key] of [['filament_g','grams'],['print_hours','hours']]){const input=document.getElementById('id_'+field);if(input)input.value=(Number(inputs.get(key))*quantity).toFixed(2);}
  feedback.textContent+='\nAplicado al primer producto. Revisa filamento y horas totales si hay más productos.';
 });
}
