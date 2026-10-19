// Exercise the actual browser scripts with DOM events; no animation dependency.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
class Element {
  constructor(dataset={}) {this.dataset=dataset;this.hidden=false;this.listeners={};this.value='';this.textContent='';this.attrs={};this.classList={toggle(){}};}
  addEventListener(name,cb){(this.listeners[name] ||= []).push(cb);}
  fire(name){for(const cb of this.listeners[name]||[])cb({target:this});}
  setAttribute(k,v){this.attrs[k]=v;} scrollIntoView(){} focus(){}
}
function runCatalog() {
 const cards=Array.from({length:9},(_,i)=>new Element({name:'Producto '+i,category:i<6?'figuras':'otros',featured:i===8?'1':'0'}));
 const grid=new Element();let order=[];grid.appendChild=c=>{order=order.filter(x=>x!==c);order.push(c);};
 const nodes={'[data-catalog-grid]':grid,'[data-catalog-search]':new Element(),'[data-catalog-sort]':new Element(),'[data-catalog-count]':new Element(),'[data-catalog-empty]':new Element(),'[data-catalog-more]':new Element()};
 const filters=['all','figuras','otros'].map(c=>new Element({catalogFilter:c}));
 const section=new Element();section.querySelector=q=>nodes[q]||null;section.querySelectorAll=q=>q==='[data-product-card]'?cards:filters;
 const doc={querySelector:q=>q==='[data-catalog]'?section:null,getElementById:()=>null,addEventListener(){}};
 vm.runInNewContext(fs.readFileSync('static/landing/js/catalog.js','utf8'),{document:doc,Map});
 const visible=()=>order.filter(c=>!c.hidden);
 assert.equal(visible().length,5);assert.equal(visible()[0],cards[8]);
 nodes['[data-catalog-more]'].fire('click');assert.equal(visible().length,9);
 filters[1].fire('click');assert.equal(visible().length,5);assert.equal(nodes['[data-catalog-more]'].attrs['aria-expanded'],'false');
 nodes['[data-catalog-more]'].fire('click');assert.equal(visible().length,6);
 nodes['[data-catalog-sort]'].value='name';nodes['[data-catalog-sort]'].fire('change');assert.equal(visible().length,5);assert.equal(visible()[0],cards[0]);
 filters[2].fire('click');assert.equal(visible().length,3);assert.equal(nodes['[data-catalog-more]'].hidden,true);
 nodes['[data-catalog-search]'].value='no existe';nodes['[data-catalog-search]'].fire('input');assert.equal(visible().length,0);assert.equal(nodes['[data-catalog-empty]'].hidden,false);
}
function runReviews(){
 const cards=Array.from({length:28},(_,i)=>new Element({reviewKind:i<7?'software':'product'}));
 const filters=['all','software','product'].map(k=>new Element({reviewFilter:k}));
 const nodes=Object.fromEntries(['[data-review-more]','[data-review-count]','[data-review-filter-empty]','[data-review-filter-status]','.reviews-filters','.reviews-toolbar'].map(k=>[k,new Element()]));
 const section={querySelector:q=>nodes[q],querySelectorAll:q=>q==='[data-review-card]'?cards:filters};
 vm.runInNewContext(fs.readFileSync('static/landing/js/review-list.js','utf8'),{document:{getElementById:()=>section}});
 const shown=()=>cards.filter(c=>!c.hidden);
 assert.equal(shown().length,5);nodes['[data-review-more]'].fire('click');assert.equal(shown().length,28);
 filters[1].fire('click');assert.equal(shown().length,5);nodes['[data-review-more]'].fire('click');assert.equal(shown().length,7);
 nodes['[data-review-more]'].fire('click');assert.equal(shown().length,5);assert.equal(nodes['[data-review-more]'].attrs['aria-expanded'],'false');
 filters[2].fire('click');assert.equal(shown().length,5);assert.ok(shown().every(c=>c.dataset.reviewKind==='product'));
}
runCatalog();runReviews();console.log('Public listing interactions passed.');
