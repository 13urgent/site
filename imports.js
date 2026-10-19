'use strict';
// Budgets et notes : table distante réservée aux administrateurs par RLS.
(()=>{
 const key='13urgent_external_drafts_v1', table='urgent_external_drafts';
 const $=id=>document.getElementById(id), form=$('externalImportForm'),list=$('externalDrafts');
 if(!form||!list)return;
 let generation=0,busy=false;
 const notice=m=>$('externalImportNotice').textContent=m;
 function localRows(){const value=JSON.parse(localStorage.getItem(key)||'[]');if(!Array.isArray(value))throw Error('Archive locale invalide.');return value;}
 function row(input){
  const text=(v,max)=>String(v??'').trim().slice(0,max);
  const data={source:text(input.source,20),reference:text(input.reference,100),origin:text(input.origin,100),destination:text(input.destination,100),pickup:input.pickup||null,vehicle:text(input.vehicle,100),weight:Number(input.weight||0),budget:Number(input.budget||0),notes:text(input.notes,800)};
  if(!['B2PWeb','Rubiwin'].includes(data.source)||!data.origin||!data.destination||!Number.isFinite(data.weight)||data.weight<0||data.weight>40000||!Number.isFinite(data.budget)||data.budget<0)throw Error('Informations de mission invalides.');
  return data;
 }
 async function admin(){
  if(!sb)throw Error('Service de connexion indisponible.');
  const {data,error}=await sb.auth.getUser();if(error||!data?.user)throw Error('Connexion administrateur requise.');
  const profile=await sb.from('profiles').select('role').eq('id',data.user.id).single();
  if(profile.error||profile.data?.role!=='admin')throw Error('Accès réservé à l’administration.');
  return data.user;
 }
 function reset(){generation++;list.replaceChildren();notice('');}
 async function draw(){
  const current=++generation;list.replaceChildren();
  try{
   await admin();const {data,error}=await sb.from(table).select('*').order('created_at',{ascending:false}).limit(100);
   if(error)throw error;if(current!==generation)return;
   if(!data.length){const p=document.createElement('p');p.textContent='Aucun brouillon partagé.';list.append(p);}
   for(const item of data){
    const wrap=document.createElement('article');wrap.className='external-item';
    for(const value of [`${item.source} · ${item.origin} → ${item.destination}`,`${item.pickup||'Date à préciser'} · ${item.vehicle||'Véhicule à préciser'} · ${item.weight} kg`,`Réf. ${item.reference||'—'} · Budget interne : ${Number(item.budget).toFixed(2)} € HT`,item.notes]){
     const p=document.createElement('p');p.textContent=value;wrap.append(p);
    }
    const del=document.createElement('button');del.type='button';del.className='btn secondary';del.textContent='Supprimer le brouillon';del.onclick=async()=>{
     if(!confirm('Supprimer ce brouillon partagé ?'))return;del.disabled=true;
     try{await admin();const result=await sb.from(table).delete().eq('id',item.id).select('id');if(result.error)throw result.error;if(!result.data?.length)throw Error('Suppression non autorisée.');await draw();}catch(e){notice('Suppression impossible : '+e.message);del.disabled=false;}
    };wrap.append(del);list.append(wrap);
   }
   notice(`${data.length} brouillon(s) partagé(s) affiché(s), 100 maximum. Aucune publication de mission.`);
  }catch(e){if(current===generation){list.replaceChildren();notice('Lecture impossible : '+e.message+' Aucun basculement vers le stockage local.');}}
 }
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(busy)return;busy=true;const button=event.submitter;button.disabled=true;
  try{const user=await admin();const payload=row(Object.fromEntries(new FormData(form)));const {error}=await sb.from(table).insert({...payload,created_by:user.id});if(error)throw error;form.reset();await draw();}
  catch(e){notice('Brouillon non enregistré : '+e.message);}finally{busy=false;button.disabled=false;}
 });
 const migrate=document.createElement('button');migrate.type='button';migrate.className='btn secondary';migrate.textContent='Copier les anciens brouillons locaux vers Supabase';
 migrate.onclick=async()=>{
  if(busy)return;
  if(!confirm('Copier les brouillons de ce navigateur dans l’espace partagé des administrateurs ? Les originaux locaux seront conservés.'))return;
  busy=true;migrate.disabled=true;
  try{
   const user=await admin();const rows=localRows();if(!rows.length)throw Error('Aucun ancien brouillon local.');
   // UUID existants conservés pour éviter les doublons lors d’une nouvelle tentative.
   const payload=rows.map(item=>{if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(item.id))throw Error('Identifiant local invalide.');return {...row(item),id:item.id,created_by:user.id};});
   const existing=await sb.from(table).select('id').in('id',payload.map(x=>x.id));if(existing.error)throw existing.error;
   const ids=new Set(existing.data.map(x=>x.id));const missing=payload.filter(x=>!ids.has(x.id));
   if(missing.length){const result=await sb.from(table).insert(missing);if(result.error)throw result.error;}
   await draw();notice(`${missing.length} brouillon(s) copié(s). Les originaux locaux sont conservés ; les identifiants déjà présents ont été ignorés.`);
  }catch(e){notice('Copie impossible : '+e.message);}finally{busy=false;migrate.disabled=false;}
 };
 form.after(migrate);$('openAdmin').addEventListener('click',draw);
 sb?.auth.onAuthStateChange(reset);
})();
