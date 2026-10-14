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

// Unit values are multiplied for every product and kept visible before saving.
function refreshUnitTotals(){
 const amount=document.getElementById('live-amount');if(!amount)return;
 const n=name=>Number(document.getElementById('id_'+name)?.value||0);
 let units=n('quantity'),price=units*n('unit_price'),grams=units*n('unit_filament_g'),hours=units*n('unit_print_hours');
 const lines=[...document.querySelectorAll('#quote-items .quote-item')].filter(line=>!line.querySelector('[name$="-DELETE"]')?.checked && (line.querySelector('[name$="-name"]')?.value.trim() || line.querySelector('[name$="-variant"]')?.value));
 if(lines.length){
  const v=(line,suffix)=>Number(line.querySelector('[name$="-'+suffix+'"]')?.value||0);
  units=lines.reduce((s,l)=>s+v(l,'quantity'),0);price=lines.reduce((s,l)=>s+v(l,'quantity')*v(l,'unit_price'),0);
  const g=lines.reduce((s,l)=>s+v(l,'quantity')*v(l,'unit_filament_g'),0),h=lines.reduce((s,l)=>s+v(l,'quantity')*v(l,'unit_print_hours'),0);
  if(g)grams=g;if(h)hours=h;
 }
 const format=v=>new Intl.NumberFormat('es-CO',{maximumFractionDigits:2}).format(v);
 amount.textContent='$ '+format(price)+' COP';document.getElementById('live-units').textContent=format(units);
 document.getElementById('live-filament').textContent=format(grams)+' g';document.getElementById('live-hours').textContent=format(hours)+' h';
}
document.getElementById('entry-form')?.addEventListener('input',refreshUnitTotals);
document.getElementById('entry-form')?.addEventListener('change',refreshUnitTotals);
document.getElementById('add-quote-item')?.addEventListener('click',refreshUnitTotals);
refreshUnitTotals();
const productData=document.getElementById('workflow-products');
if(productData){
 const products=JSON.parse(productData.textContent),variants=JSON.parse(document.getElementById('workflow-variants')?.textContent||'[]');
 const productById=id=>products.find(p=>String(p.id)===id);
 const rootSelect=document.getElementById('id_reference_product');
 function preview(){
  const p=productById(rootSelect?.value),panel=document.getElementById('selected-product-preview'),image=document.getElementById('selected-product-image');
  if(!panel)return;panel.hidden=!p;if(!p)return;
  document.getElementById('selected-product-info').textContent=p.name+' · '+p.category;
  image.hidden=!p.image;if(p.image)image.src=p.image;else image.removeAttribute('src');image.alt=p.name;
 }
 function fillRoot(p){
  for(const [field,value] of Object.entries({title:p.name,description:p.description,product_category:p.category_id,unit_price:p.price,unit_filament_g:p.unit_filament_g,unit_print_hours:p.unit_print_hours,amount:p.price,filament_g:p.unit_filament_g,print_hours:p.unit_print_hours})){
   const input=document.getElementById('id_'+field);if(input)input.value=value;
  }
  const quantity=document.getElementById('id_quantity');if(quantity&&!quantity.value)quantity.value=1;
  preview();refreshUnitTotals();
 }
 function restrictVariants(line){
  const product=line.querySelector('[name$="-product"]')?.value,select=line.querySelector('[name$="-variant"]');if(!select)return;
  for(const option of select.options){const v=variants.find(v=>String(v.id)===option.value);option.hidden=!!(product&&v&&String(v.product_id)!==product);option.disabled=option.hidden;}
  if(select.selectedOptions[0]?.disabled)select.value='';
 }
 function fillLine(line,p,v){
  const values={name:v?p.name+' · '+v.name:p.name,description:p.description,unit_price:v?v.estimated_price:p.price,unit_filament_g:p.unit_filament_g,unit_print_hours:p.unit_print_hours,length_cm:v?.length_cm||0,width_cm:v?.width_cm||0,height_cm:v?.height_cm||0};
  for(const [field,value] of Object.entries(values)){const input=line.querySelector('[name$="-'+field+'"]');if(input)input.value=value;}
  const quantity=line.querySelector('[name$="-quantity"]');if(quantity&&!quantity.value)quantity.value=1;
  const title=document.getElementById('id_title');if(title&&!title.value)title.value=p.name;
  restrictVariants(line);refreshUnitTotals();
 }
 rootSelect?.addEventListener('change',()=>{const p=productById(rootSelect.value);if(p)fillRoot(p);else preview();});preview();
 document.querySelectorAll('#quote-items .quote-item').forEach(restrictVariants);
 document.getElementById('quote-items')?.addEventListener('change',event=>{
  const line=event.target.closest('.quote-item');if(!line)return;
  if(event.target.name?.endsWith('-product')){restrictVariants(line);const p=productById(event.target.value);if(p){const variant=line.querySelector('[name$="-variant"]');if(variant)variant.value='';fillLine(line,p);}}
  if(event.target.name?.endsWith('-variant')){const v=variants.find(v=>String(v.id)===event.target.value),p=v&&productById(String(v.product_id));if(p){line.querySelector('[name$="-product"]').value=p.id;fillLine(line,p,v);}}
 });
}

const batchForm=document.getElementById('bulk-delete-form');
if(batchForm){
 const boxes=[...batchForm.querySelectorAll('input[name="entries"]')],selectPage=document.getElementById('select-page');
 const count=document.getElementById('selected-count'),submit=batchForm.querySelector('button[type="submit"]');
 function selection(){const chosen=boxes.filter(box=>box.checked).length;if(count)count.textContent='('+chosen+')';if(submit)submit.disabled=chosen===0;if(selectPage){selectPage.checked=chosen===boxes.length&&chosen>0;selectPage.indeterminate=chosen>0&&chosen<boxes.length;}}
 selectPage?.addEventListener('change',()=>{boxes.forEach(box=>{box.checked=selectPage.checked;});selection();});
 boxes.forEach(box=>box.addEventListener('change',selection));selection();
}
