'use strict';
// Préparation manuelle des missions externes : stockage local, pas de synchronisation API.
(()=>{
 const key='13urgent_external_drafts_v1';
 const $=id=>document.getElementById(id);
 const read=()=>{try{return JSON.parse(localStorage.getItem(key)||'[]')}catch{return []}};
 const write=v=>localStorage.setItem(key,JSON.stringify(v));
 const form=$('externalImportForm'), list=$('externalDrafts');
 if(!form||!list)return;
 function draw(){list.replaceChildren();const items=read();if(!items.length){const p=document.createElement('p');p.textContent='Aucune mission externe préparée.';list.append(p);return;}
 items.slice().reverse().forEach(item=>{
 const wrap=document.createElement('div');wrap.className='external-item';
 const heading=document.createElement('strong');heading.textContent=`${item.source} · ${item.origin} → ${item.destination}`;
 const desc=document.createElement('p');desc.textContent=`${item.pickup||'Date à préciser'} · ${item.vehicle||'Véhicule à préciser'} · ${item.weight||0} kg · Statut : brouillon non publié`;
 const ref=document.createElement('p');ref.textContent=`Référence : ${item.reference||'—'} · Budget interne : ${item.budget?item.budget+' € HT':'non renseigné'}`;
 const del=document.createElement('button');del.type='button';del.className='btn ghost';del.textContent='Supprimer';del.addEventListener('click',()=>{write(read().filter(x=>x.id!==item.id));draw()});
 wrap.append(heading,desc,ref,del);list.append(wrap);
 });}
 form.addEventListener('submit',event=>{event.preventDefault();if($('openAdmin').hidden){$('externalImportNotice').textContent='Connexion administrateur requise.';return;}
 const f=new FormData(form);const item={id:crypto.randomUUID(),source:String(f.get('source')),reference:String(f.get('reference')).trim(),origin:String(f.get('origin')).trim(),destination:String(f.get('destination')).trim(),pickup:String(f.get('pickup')),vehicle:String(f.get('vehicle')).trim(),weight:Number(f.get('weight'))||0,budget:Number(f.get('budget'))||0,notes:String(f.get('notes')).trim(),createdAt:new Date().toISOString()};
 if(!item.origin||!item.destination)return;write([...read(),item]);form.reset();$('externalImportNotice').textContent='Brouillon enregistré sur cet ordinateur uniquement. Aucune publication ni transmission externe.';draw();});
 $('openAdmin').addEventListener('click',draw);
 draw();
})();
