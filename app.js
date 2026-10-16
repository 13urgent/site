'use strict';
const KEY='13urgent_demo_shipments_v1';
const $=id=>document.getElementById(id);
function load(){try{const v=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(v)?v:[]}catch{return []}}
function save(v){localStorage.setItem(KEY,JSON.stringify(v))}
function el(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n}
function dateLabel(s){const d=new Date(s);return Number.isNaN(d.getTime())?s:new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(d)}
function render(){
 const list=$('shipments');list.replaceChildren();
 const query=$('courseSearch').value.trim().toLocaleLowerCase('fr');
 const vehicle=$('courseVehicle').value;
 const shipments=load().filter(s=>s.status!=='cancelled'&&(!vehicle||s.vehicle===vehicle)&&(!query||`${s.origin} ${s.destination}`.toLocaleLowerCase('fr').includes(query)));
 $('courseCount').textContent=`${shipments.length} demande(s) de démonstration`;
 if(!shipments.length)list.append(el('div','empty','Aucune demande ne correspond à votre recherche.'));
 for(const s of shipments.slice().reverse()){
  const card=el('article','shipment'),info=el('div');info.append(el('span','tag',s.vehicle),el('h3','',`${s.origin} → ${s.destination}`),el('p','',`Enlèvement : ${dateLabel(s.pickup)} · ${s.pallets} palette(s) · ${s.weight} kg`),el('p','',`Réf. ${s.id} · Demande de ${s.company}`));
  const b=el('button','btn secondary','Offres en ligne non activées');b.type='button';b.disabled=true;card.append(info,b);list.append(card);
 }
 renderTracking();
}
function renderTracking(){
 const host=$('shipmentTracking');host.replaceChildren();const rows=load();$('exportShipments').disabled=!rows.length;
 if(!rows.length)host.append(el('p','','Aucune demande enregistrée dans ce navigateur.'));
 for(const s of rows.slice().reverse()){
  const card=el('article','dossier');card.append(el('h3','',`${s.origin} → ${s.destination}`),el('p','',`${s.id} · ${s.status==='cancelled'?'Annulée localement':'Enregistrée localement'} · ${dateLabel(s.pickup)}`));
  if(s.notes)card.append(el('p','',s.notes));
  if(s.status!=='cancelled'){
   const cancel=el('button','btn secondary','Annuler la demande locale');cancel.type='button';cancel.addEventListener('click',()=>{
    if(!confirm('Annuler cette demande de démonstration dans ce navigateur ?'))return;
    const items=load();const item=items.find(x=>x.id===s.id);if(!item)return;item.status='cancelled';item.cancelledAt=new Date().toISOString();
    try{save(items);render();$('trackingNotice').textContent='Demande annulée localement. Aucun transporteur n’a été contacté.';}catch{$('trackingNotice').textContent='Enregistrement impossible : vérifiez le stockage du navigateur.';}
   });card.append(cancel);
  }
  host.append(card);
 }
}
$('courseFilters').addEventListener('submit',e=>e.preventDefault());
$('courseSearch').addEventListener('input',render);$('courseVehicle').addEventListener('change',render);
$('exportShipments').addEventListener('click',()=>{
 const url=URL.createObjectURL(new Blob([JSON.stringify({version:1,exportedAt:new Date().toISOString(),shipments:load()},null,2)],{type:'application/json'}));
 const link=el('a');link.href=url;link.download='13urgent-demandes-locales.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 $('trackingNotice').textContent='Export créé. Il contient vos coordonnées et les détails de vos demandes : conservez-le dans un endroit privé.';
});
$('shipmentForm').addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.currentTarget);const obj={id:'DEMO-'+Date.now().toString(36).toUpperCase(),company:String(f.get('company')).trim(),email:String(f.get('email')).trim(),origin:String(f.get('origin')).trim(),destination:String(f.get('destination')).trim(),pickup:String(f.get('pickup')),vehicle:String(f.get('vehicle')),pallets:Number(f.get('pallets')),weight:Number(f.get('weight')),notes:String(f.get('notes')).trim(),createdAt:new Date().toISOString(),offers:[]};if(!obj.company||!obj.email||!obj.origin||!obj.destination||!obj.pickup||!obj.vehicle){return}const rows=load();rows.push(obj);try{save(rows);}catch{$('formNotice').hidden=false;$('formNotice').textContent='Enregistrement impossible : vérifiez le stockage du navigateur.';return;}e.currentTarget.reset();$('formNotice').hidden=false;$('formNotice').textContent=`Demande ${obj.id} enregistrée dans ce navigateur uniquement. Elle n'a été transmise à personne.`;render();$('courses').scrollIntoView({behavior:'smooth'})});
render();
