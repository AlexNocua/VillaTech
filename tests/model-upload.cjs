const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function scenario(){
 const file={files:[{name:'modelo.3mf',size:12000}],validity:'',setCustomValidity(v){this.validity=v;},addEventListener(){}};
 const status={textContent:''},progress={hidden:true,value:0},button={disabled:false};
 let submit,request;
 const form={action:'/gestion/modelos/',querySelector:q=>q==='input[type=file]'?file:q==='button[type=submit]'?button:q==='progress'?progress:status,addEventListener:(n,cb)=>submit=cb,reportValidity:()=>!file.validity,setAttribute(){},removeAttribute(){}};
 class Request{constructor(){request=this;this.upload={};}open(){}setRequestHeader(){}send(){this.sent=true;}}
 vm.runInNewContext(fs.readFileSync('static/landing/js/model-upload.js','utf8'),{document:{querySelector:()=>form},XMLHttpRequest:Request,FormData:class{},location:{href:'/gestion/modelos/'}});
 return {file,status,progress,button,submit:()=>submit({preventDefault(){}}),request:()=>request};
}
let s=scenario();s.file.files[0].size=101*1024*1024;s.submit();assert.match(s.file.validity,/100 MB/);assert.equal(s.request(),undefined);
s=scenario();s.submit();assert.equal(s.button.disabled,true);s.submit();const request=s.request();assert.equal(request.sent,true);request.upload.onprogress({lengthComputable:true,loaded:50,total:100});assert.equal(s.progress.value,50);
request.status=413;request.onload();assert.equal(s.button.disabled,false);assert.match(s.status.textContent,/tamaño/);assert.equal(s.file.files[0].name,'modelo.3mf');
s=scenario();s.submit();s.request().ontimeout();assert.equal(s.button.disabled,false);assert.match(s.status.textContent,/podría haberse guardado/);
console.log('Model upload validation, progress, recovery and timeout passed.');
