'use strict';
const PRODUCTION = 'https://www.villatechubate.com';
const configured = process.env.EXPO_PUBLIC_VILLATECH_ORIGIN || PRODUCTION;
const root = new URL(configured);
if (root.protocol !== 'https:' || root.username || root.password || root.pathname !== '/' || root.search || root.hash || root.port) {
  throw new Error('Configura EXPO_PUBLIC_VILLATECH_ORIGIN con un origen HTTPS sin ruta.');
}
const ORIGIN = root.origin;
const HOSTS = new Set(ORIGIN === PRODUCTION ? [root.hostname, 'villatechubate.com'] : [root.hostname]);
const ROUTES = [
  {key:'home',label:'Inicio',icon:'⌂',path:'/gestion/'},
  {key:'quotes',label:'Cotizar',icon:'✎',path:'/gestion/flujo/nuevo/'},
  {key:'orders',label:'Pedidos',icon:'▤',path:'/gestion/flujo/?stage=orders'},
  {key:'delivery',label:'Entregas',icon:'▦',path:'/gestion/calendario/entregas/'},
  {key:'more',label:'Gestión',icon:'☰',path:'/gestion/flujo/'}
];
function classify(url) {
  try {
    const u = new URL(url);
    if (u.protocol === 'https:' && HOSTS.has(u.hostname) && !u.username && !u.password && (!u.port || u.port === '443')) return 'internal';
    if (['https:','mailto:','tel:'].includes(u.protocol) && !u.username && !u.password) return 'external';
  } catch (_) {}
  return 'blocked';
}
function routeUrl(path) {
  const u = new URL(path, ORIGIN);
  if (classify(u.href) !== 'internal' || u.origin !== ORIGIN || !u.pathname.startsWith('/gestion/')) throw new Error('Ruta no permitida');
  return u.href;
}
function mayHaveUnsavedForm(url) { try {const p=new URL(url).pathname; return /\/gestion\/(flujo\/(nuevo|\d+\/editar)|registro\/[^/]+|productos\/(nuevo|\d+\/editar))\/?/.test(p); } catch (_) {return false;} }
module.exports={ORIGIN,ROUTES,classify,routeUrl,mayHaveUnsavedForm};
