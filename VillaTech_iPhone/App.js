import React, {useRef, useState} from 'react';
import {ActivityIndicator, Alert, Image, Linking, Pressable, ScrollView, StatusBar, StyleSheet, Text, View} from 'react-native';
import {SafeAreaProvider, SafeAreaView} from 'react-native-safe-area-context';
import {File, Paths} from 'expo-file-system';
import Drafts,{fields} from './Drafts';
import {WebView} from 'react-native-webview';
const {ORIGIN, ROUTES, classify, routeUrl, mayHaveUnsavedForm} = require('./navigation.cjs');

const draftFile=new File(Paths.document, ORIGIN === 'https://www.villatechubate.com' ? 'villatech-drafts-v1.json' : 'villatech-drafts-' + new URL(ORIGIN).hostname + '.json');
function AppScreen() {
  const [drafts,setDrafts]=useState(()=>{try{return draftFile.exists?JSON.parse(draftFile.textSync()):[];}catch{return [];}});
  const [offline,setOffline]=useState(false);
  const [transfer,setTransfer]=useState(null);
  function persist(rows) {
    try {draftFile.writeSync(JSON.stringify(rows));setDrafts(rows);return true;}
    catch {Alert.alert('No se pudo guardar en el dispositivo');return false;}
  }
  function fillDraft() {
    if(!transfer||classify(current)!=='internal'||new URL(current).pathname!=='/gestion/flujo/nuevo/') {
      Alert.alert('Abre primero Nueva cotización e inicia sesión si es necesario');return;
    }
    const data=fields.map(([k])=>[k,transfer.values[k]||'']).filter(([,v])=>v!=='');
    web.current?.injectJavaScript(`(()=>{if(!${JSON.stringify(ORIGIN === 'https://www.villatechubate.com' ? [ORIGIN,'https://villatechubate.com'] : [ORIGIN])}.includes(location.origin)||location.pathname!=='/gestion/flujo/nuevo/')return;const form=document.getElementById('entry-form');if(!form)return;for(const [name,value] of ${JSON.stringify(data)}){const el=form.elements.namedItem(name);if(el instanceof HTMLInputElement||el instanceof HTMLTextAreaElement){el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}}form.scrollIntoView({block:'start'});})();true;`);
  }

  const web = useRef(null);
  const [uri, setUri] = useState(routeUrl('/gestion/'));
  const [current, setCurrent] = useState(routeUrl('/gestion/'));
  const [active, setActive] = useState('home');
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [canGoBack, setCanGoBack] = useState(false);

  const confirmLeave = (fn) => {
    if (!mayHaveUnsavedForm(current)) { fn(); return; }
    Alert.alert('¿Salir de este formulario?', 'Si tienes cambios sin guardar, puedes perderlos.', [
      {text: 'Seguir editando', style: 'cancel'},
      {text: 'Salir', style: 'destructive', onPress: fn},
    ]);
  };
  const go = (route) => confirmLeave(() => {
    const target = routeUrl(route.path);
    setFailed(false); setActive(route.key);
    if (web.current && classify(current) === 'internal') web.current.injectJavaScript('window.location.assign(' + JSON.stringify(target) + '); true;');
    else setUri(target);
  });
  const back = () => { if (canGoBack) confirmLeave(() => web.current?.goBack()); };
  const external = (url) => {
    if (classify(url) !== 'external') return;
    Alert.alert('Abrir enlace externo', 'Este enlace se abrirá fuera de VillaTech Gestión.', [
      {text: 'Cancelar', style: 'cancel'},
      {text: 'Abrir', onPress: () => Linking.openURL(url).catch(() => Alert.alert('No se pudo abrir el enlace'))},
    ]);
  };
  const shouldStart = ({url}) => {
    const kind = classify(url);
    if (kind === 'internal' && new URL(url).pathname === '/gestion/avisos/gmail/') {
      Linking.openURL(url).catch(() => Alert.alert('Abre Gestión → Correos desde Safari'));
      return false;
    }
    if (kind === 'internal') return true;
    if (kind === 'external') external(url);
    return false;
  };
  const openWindow = (event) => {
    const url = event.nativeEvent.targetUrl;
    const kind = classify(url);
    if (kind === 'internal') web.current?.injectJavaScript('window.location.assign(' + JSON.stringify(url) + '); true;');
    else if (kind === 'external') external(url);
  };

  return <SafeAreaView style={styles.safe} edges={['top','bottom']}>
    <StatusBar barStyle="dark-content" />
    <View style={styles.header}>
      <Image source={require('./assets/icon.png')} style={styles.logo} accessibilityIgnoresInvertColors />
      <View style={styles.heading}><Text style={styles.brand}>VillaTech</Text><Text style={styles.caption}>TU ESTUDIO EN MOVIMIENTO</Text></View>
      <Pressable accessibilityRole="button" accessibilityLabel="Volver a la página anterior" accessibilityState={{disabled:!canGoBack}} onPress={back} disabled={!canGoBack} style={[styles.headerAction,!canGoBack&&styles.muted]}><Text style={styles.headerActionText}>‹</Text></Pressable>
      <Pressable accessibilityRole="button" accessibilityLabel="Recargar página" onPress={() => confirmLeave(() => {setFailed(false);web.current?.reload();})} style={styles.headerAction}><Text style={styles.reload}>↻</Text></Pressable>
    </View>
    <Pressable onPress={()=>offline?setOffline(false):confirmLeave(()=>setOffline(true))} style={{padding:12,backgroundColor:'#eaf7ec'}}><Text style={{color:'#0b6e34',fontWeight:'700'}}>{offline?'← Volver a gestión en línea':'✎ Borradores sin conexión'}</Text></Pressable>
    {<View style={{flex:1,display:offline?'flex':'none'}}><Drafts drafts={drafts} persist={persist} onTransfer={draft=>{setTransfer(draft);setOffline(false);go(ROUTES[1]);}}/></View>}
    {transfer&&!offline&&<Pressable style={{padding:12}} onPress={()=>Alert.alert('Copiar borrador al formulario','Se reemplazarán los campos incluidos en el borrador. Revisa y guarda en la web.',[{text:'Cancelar',style:'cancel'},{text:'Copiar',onPress:fillDraft}])}><Text style={{color:'#0b6e34'}}>Pegar borrador seleccionado</Text></Pressable>}
    <View style={[styles.screen,offline&&{display:'none'}]}>
      <WebView ref={web} source={{uri}} style={styles.web} originWhitelist={['*']}
        onShouldStartLoadWithRequest={shouldStart} onOpenWindow={openWindow}
        onNavigationStateChange={(state) => {setCurrent(state.url);setCanGoBack(state.canGoBack);}}
        onLoadStart={() => {setLoading(true);setFailed(false);}} onLoadEnd={() => setLoading(false)}
        onError={() => {setLoading(false);setFailed(true);}}
        sharedCookiesEnabled javaScriptEnabled domStorageEnabled allowsBackForwardNavigationGestures
        allowsInlineMediaPlayback setSupportMultipleWindows />
      {loading && !failed && <View pointerEvents="none" style={styles.loading}><ActivityIndicator color="#159447" size="small"/><Text style={styles.loadingText}>Conectando con tu estudio…</Text></View>}
      {failed && <View style={styles.error} accessibilityRole="alert"><Text style={styles.errorIcon}>☁</Text><Text style={styles.errorTitle}>No pudimos conectar</Text><Text style={styles.errorText}>Revisa tu conexión y vuelve a intentarlo. Si estabas guardando, revisa el registro antes de repetir la operación.</Text><Pressable style={styles.retry} onPress={() => {setFailed(false);web.current?.reload();}}><Text style={styles.retryText}>Intentar de nuevo</Text></Pressable><Text style={styles.errorFoot}>La app requiere conexión a Internet.</Text></View>}
    </View>
    <View style={[styles.nav,offline&&{display:'none'}]} accessibilityRole="tablist">{ROUTES.map(route => <Pressable key={route.key} onPress={() => go(route)} accessibilityRole="tab" accessibilityLabel={route.label} accessibilityState={{selected:active===route.key}} style={[styles.navItem, active===route.key&&styles.navActive]}><Text style={[styles.navIcon,active===route.key&&styles.navSelected]}>{route.icon}</Text><Text style={[styles.navLabel,active===route.key&&styles.navSelected]}>{route.label}</Text></Pressable>)}</View>
  </SafeAreaView>;
}
export default function App(){return <SafeAreaProvider><AppScreen /></SafeAreaProvider>;}
const styles=StyleSheet.create({
 safe:{flex:1,backgroundColor:'#fff'},header:{height:66,flexDirection:'row',alignItems:'center',paddingHorizontal:15,borderBottomWidth:1,borderBottomColor:'#e7ede9',backgroundColor:'#fff'},logo:{height:44,width:44,borderRadius:22,marginRight:9},heading:{flex:1},brand:{fontSize:20,fontWeight:'800',color:'#07182a',letterSpacing:-.6},caption:{fontSize:8,fontWeight:'700',letterSpacing:1,color:'#159447',marginTop:2},headerAction:{width:40,height:40,alignItems:'center',justifyContent:'center',borderRadius:12,backgroundColor:'#f2f7f3',marginLeft:7},headerActionText:{fontSize:32,color:'#0b6e34',lineHeight:36},reload:{fontSize:24,color:'#0b6e34'},muted:{opacity:.35},screen:{flex:1,backgroundColor:'#f6f9f6'},web:{flex:1,backgroundColor:'#fff'},loading:{position:'absolute',top:12,alignSelf:'center',flexDirection:'row',gap:8,alignItems:'center',backgroundColor:'#fff',paddingHorizontal:15,paddingVertical:9,borderRadius:20,shadowColor:'#07182a',shadowOpacity:.12,shadowRadius:10,elevation:3},loadingText:{fontSize:12,color:'#263b30'},error:{...StyleSheet.absoluteFillObject,backgroundColor:'#f6f9f6',alignItems:'center',justifyContent:'center',padding:30},errorIcon:{fontSize:45,color:'#159447'},errorTitle:{fontSize:22,fontWeight:'800',color:'#07182a',marginTop:10},errorText:{textAlign:'center',color:'#526058',fontSize:14,lineHeight:22,marginVertical:17},retry:{backgroundColor:'#159447',borderRadius:14,paddingVertical:14,paddingHorizontal:24},retryText:{color:'#fff',fontWeight:'700'},errorFoot:{fontSize:11,color:'#6b7470',marginTop:18},nav:{flexDirection:'row',paddingHorizontal:8,paddingTop:7,paddingBottom:4,borderTopWidth:1,borderTopColor:'#e7ede9',backgroundColor:'#fff'},navItem:{flex:1,alignItems:'center',justifyContent:'center',height:52,borderRadius:13},navActive:{backgroundColor:'#eaf7ec'},navIcon:{fontSize:22,lineHeight:25,color:'#69776e'},navLabel:{fontSize:10,color:'#69776e',fontWeight:'600',marginTop:2},navSelected:{color:'#0b6e34',fontWeight:'800'},
});
