const test=require('node:test'),assert=require('node:assert/strict');
const {ORIGIN,ROUTES,classify,routeUrl,mayHaveUnsavedForm}=require('../navigation.cjs');
test('menu links are HTTPS VillaTech management routes',()=>{
 for(const r of ROUTES) {const u=routeUrl(r.path); assert.ok(u.startsWith(ORIGIN+'/gestion/'));assert.equal(classify(u),'internal');}
});
test('lookalike sites and insecure URLs cannot enter the management view',()=>{
 assert.equal(classify('https://www.villatechubate.com.evil.example/gestion/'),'external');
 assert.equal(classify('https://evil.example@villatechubate.com/gestion/'),'blocked');
 assert.equal(classify('http://www.villatechubate.com/'),'blocked');
 assert.equal(classify('javascript:alert(1)'),'blocked');
 assert.throws(()=>routeUrl('https://evil.example'));
});
test('editing warning only applies to possible forms',()=>{
 assert.equal(mayHaveUnsavedForm(ORIGIN+'/gestion/flujo/nuevo/'),true);
 assert.equal(mayHaveUnsavedForm(ORIGIN+'/gestion/flujo/3/editar/'),true);
 assert.equal(mayHaveUnsavedForm(ORIGIN+'/gestion/calendario/'),false);
});
