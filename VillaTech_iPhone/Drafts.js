import React,{useState} from 'react';
import {Alert,Pressable,ScrollView,Text,TextInput,View} from 'react-native';
export const fields=[
 ['title','Trabajo'],['customer','Cliente'],['customer_phone','Teléfono'],['customer_email','Correo'],
 ['description','Descripción'],['quantity','Cantidad'],['unit_price','Precio unitario (COP)'],
 ['unit_filament_g','Filamento por unidad (g)'],['unit_print_hours','Horas por unidad'],
 ['estimated_delivery_date','Entrega estimada (AAAA-MM-DD)'],
];
const empty=()=>({quantity:'1'});
function Button({title,onPress}) {return <Pressable onPress={onPress} style={{padding:13,backgroundColor:'#eaf7ec',borderRadius:9,marginVertical:4}}><Text style={{color:'#0b6e34',fontWeight:'700'}}>{title}</Text></Pressable>;}
export default function Drafts({drafts,persist,onTransfer}) {
 const [values,setValues]=useState(empty),[id,setId]=useState(null);
 const current=drafts.find(x=>x.id===id);
 const dirty=JSON.stringify(values)!==JSON.stringify(current?.values||empty());
 const change=(fn)=>dirty?Alert.alert('Cambios sin guardar','¿Descartar los cambios de este formulario?',[{text:'Cancelar',style:'cancel'},{text:'Descartar',style:'destructive',onPress:fn}]):fn();
 const save=()=>{
  if(!values.title?.trim()||!values.customer?.trim()||!/^\d+$/.test(values.quantity||'')||Number(values.quantity)<1) return Alert.alert('Completa el trabajo, el cliente y una cantidad válida');
  const key=id||Date.now().toString();
  if(persist([{id:key,values},...drafts.filter(x=>x.id!==key)])){setId(key);Alert.alert('Guardado en este iPhone','Todavía no se ha registrado en VillaTech.');}
 };
 return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:16,paddingBottom:32,gap:8}}>
  <Text style={{fontSize:25,fontWeight:'800',color:'#07182a'}}>Cotizaciones sin conexión</Text>
  <Text>Prepara y guarda un borrador. Cuando tengas internet, pásalo al formulario web, revísalo y guarda allí.</Text>
  <Button title="+ Nuevo borrador" onPress={()=>change(()=>{setValues(empty());setId(null);})}/>
  {drafts.map(d=><Button key={d.id} title={d.values.title+' · '+d.values.customer} onPress={()=>change(()=>{setValues(d.values);setId(d.id);})}/>)}
  {fields.map(([key,label])=><View key={key} style={{gap:4}}><Text>{label}</Text><TextInput accessibilityLabel={label} value={values[key]||''} onChangeText={v=>setValues(p=>({...p,[key]:v}))} maxLength={key==='description'?3000:180} multiline={key==='description'} autoCapitalize={key==='customer_email'?'none':'sentences'} style={{borderWidth:1,borderColor:'#ccdacf',borderRadius:10,padding:10,minHeight:44,color:'#07182a'}}/></View>)}
  <Button title="Guardar en este iPhone" onPress={save}/>
  {current&&!dirty&&<Button title="Abrir formulario web para transferir" onPress={()=>onTransfer(current)}/>}
  {current&&<Button title="Eliminar borrador local" onPress={()=>Alert.alert('¿Eliminar borrador?','Solo se elimina la copia local.',[{text:'Cancelar',style:'cancel'},{text:'Eliminar',style:'destructive',onPress:()=>{if(persist(drafts.filter(x=>x.id!==id))){setValues(empty());setId(null);}}}])}/>}
 </ScrollView>;
}
