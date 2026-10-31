'use strict';
(()=>{
 const bucket='urgent-mission-files';
 const names={goods:'Photo de marchandise',reservation:'Photo et réserves',waybill:'Lettre de voiture'};
 let generation=0,policyPromise=null,busy=0,sessionUserId=null;
 const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const rpc=async(name,args)=>{let q=sb.rpc(name,args);if(typeof q.abortSignal==='function')q=q.abortSignal(AbortSignal.timeout(20000));const r=await q;if(r.error)throw r.error;return r.data;};
 async function timed(request){let timer;try{return await Promise.race([request,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Délai réseau dépassé ; l’envoi doit être vérifié.')),45000);})]);}finally{clearTimeout(timer);}}
 async function policy(){if(!policyPromise)policyPromise=rpc('urgent_mobile_mission_policy',{}).catch(()=>null);return policyPromise;}
 async function sameUser(id){const r=await sb.auth.getUser();if(r.error||r.data?.user?.id!==id)throw Error('La session a changé. Reconnectez-vous.');}
 async function files(id){
  const all=[];for(let offset=0;;offset+=100){const r=await sb.from('urgent_mission_files').select('id,kind,caption,storage_path,original_filename,created_at').eq('shipment_id',id).order('created_at',{ascending:false}).order('id').range(offset,offset+99);if(r.error)throw r.error;all.push(...r.data||[]);if((r.data||[]).length<100)return all;}
 }
 function button(text,action){const b=el('button',text,'btn secondary');b.type='button';b.onclick=async()=>{b.disabled=true;try{await action();}finally{b.disabled=false;}};return b;}
 function attach(card,shipment,profile,contact){
  if(!sb||card.querySelector('.mission-tools'))return;sessionUserId=profile.id;
  const current=generation;
  const host=el('section',undefined,'mission-tools');host.append(el('h4','Navigation et documents de la course'));
  const notice=el('p',undefined,'offer-feedback');notice.hidden=true;notice.setAttribute('role','status');
  const show=(text,error=false)=>{if(!card.isConnected||current!==generation)return;notice.hidden=false;notice.textContent=text;notice.classList.toggle('danger',error);};
  host.append(notice);card.append(host);
  const valid=()=>current===generation&&card.isConnected;
  const userId=profile.id;
  (async()=>{
   const ready=await policy();if(!valid())return;
   if(!ready?.enabled||!ready.private_files||!ready.addresses){if(document.body.dataset.mobileApp==='true')show('Les photos, lettres de voiture et adresses GPS doivent encore être activées par l’administration.');else host.remove();return;}
   const intro=document.querySelector('#suivi .section-head p');if(intro)intro.textContent='Suivi et pièces partagés entre les parties. La livraison déclarée par le transporteur reste à confirmer par le donneur d’ordre.';
   let pickup=contact?.pickup_address||'',delivery=contact?.delivery_address||'';
   const navigation=el('div',undefined,'mission-navigation');
   function drawNavigation(){
    navigation.replaceChildren();if(profile.role!=='carrier'||shipment.assigned_company_id!==profile.company_id)return;
    navigation.append(el('p','Ouvrez votre GPS et vérifiez que l’itinéraire convient au gabarit et au poids de votre véhicule.'));
    for(const[label,address,city]of[['Enlèvement',pickup,shipment.origin],['Livraison',delivery,shipment.destination]]){
     const row=el('div',undefined,'mission-route');row.append(el('strong',label),el('p',address||'Adresse exacte non renseignée — ville : '+city));
     if(!address){row.append(el('p','Demandez l’adresse complète au donneur d’ordre avant de partir.','muted'));navigation.append(row);continue;}
     for(const[name,url]of[['Google Maps','https://www.google.com/maps/dir/?api=1&travelmode=driving&destination='+encodeURIComponent(address)],['Waze','https://waze.com/ul?navigate=yes&q='+encodeURIComponent(address)]]){const a=el('a',name,'btn secondary');a.href=url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);}
     navigation.append(row);
    }
   }
   drawNavigation();host.append(navigation);
   const lateAddresses=!['open','assigned'].includes(shipment.status);
   if(shipment.owner_company_id===profile.company_id&&!shipment.archived_at&&(['open','assigned'].includes(shipment.status)||['heading_pickup','at_pickup','loaded'].includes(shipment.status)&&(!pickup||!delivery))){
    const details=el('details');details.append(el('summary','Renseigner les adresses exactes du GPS'));
    const form=el('form',undefined,'mission-address-form');
    for(const[name,label,value]of[['pickup','Adresse complète d’enlèvement',pickup],['delivery','Adresse complète de livraison',delivery]]){const l=el('label',label);const i=el('textarea');i.name=name;i.required=true;i.minLength=5;i.maxLength=500;i.value=value;i.disabled=lateAddresses&&Boolean(value);l.append(i);form.append(l);}
    if(lateAddresses)form.append(el('p','Complétez les adresses manquantes. Les adresses déjà renseignées restent figées après le départ.','muted'));
    const save=el('button','Enregistrer les adresses','btn primary');save.type='submit';form.append(save);details.append(form);host.append(details);
    form.onsubmit=async e=>{e.preventDefault();if(save.disabled||!form.reportValidity())return;save.disabled=true;busy++;try{await sameUser(userId);await rpc('urgent_save_mission_addresses',{p_shipment:shipment.id,p_pickup:form.elements.pickup.value.trim(),p_delivery:form.elements.delivery.value.trim()});if(!valid())return;pickup=form.elements.pickup.value.trim();delivery=form.elements.delivery.value.trim();drawNavigation();show('Adresses enregistrées et accessibles au transporteur attribué.');}catch(e){show('Adresses non confirmées : '+e.message,true);}finally{save.disabled=false;busy--;}};
   }
   const list=el('div',undefined,'mission-file-list');list.setAttribute('aria-label','Documents de la course');host.append(list);
   async function load(){
    const rows=await files(shipment.id);if(!valid())return;list.replaceChildren();
    if(!rows.length)list.append(el('p','Aucune photo ni lettre de voiture partagée pour cette course.','muted'));
    for(const file of rows){
     const item=el('article',undefined,'doc-item');item.append(el('strong',names[file.kind]||'Pièce de course'),el('p',file.original_filename+' · Déposé le '+new Date(file.created_at).toLocaleString('fr-FR',{timeZone:'Europe/Paris'})));
     if(file.caption)item.append(el('p',file.caption));
     item.append(button('Accéder au fichier privé',async()=>{try{await sameUser(userId);const r=await sb.storage.from(bucket).createSignedUrl(file.storage_path,60);if(r.error)throw r.error;if(!valid())return;const url=new URL(r.data?.signedUrl);if(url.protocol!=='https:'||url.origin!==new URL(window.URGENT_SUPABASE_URL).origin||!url.pathname.includes('/storage/v1/object/sign/'+bucket+'/'))throw Error('Lien privé non vérifié.');item.querySelector('.mission-private-link')?.remove();const a=el('a','Ouvrir le fichier — lien valable 60 secondes','btn secondary mission-private-link');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';item.append(a);}catch(e){show('Ouverture impossible : '+e.message,true);}}));list.append(item);
    }
   }
   await load();if(!valid())return;
   if(profile.role!=='carrier'||shipment.assigned_company_id!==profile.company_id||shipment.archived_at||['open','cancelled'].includes(shipment.status))return;
   const details=el('details');details.append(el('summary','Ajouter une photo ou une lettre de voiture'));
   const form=el('form',undefined,'mission-upload-form');
   const label=el('label','Type de pièce');const kind=el('select');kind.name='kind';for(const[value,title]of Object.entries(names)){const o=el('option',title);o.value=value;kind.append(o);}label.append(kind);form.append(label);
   const captionLabel=el('label','Précisions ou réserves constatées');const caption=el('textarea');caption.name='caption';caption.maxLength=2000;captionLabel.append(caption);form.append(captionLabel);
   const cameraLabel=el('label','Prendre une photo avec le téléphone');const camera=el('input');camera.type='file';camera.accept='image/jpeg,image/png';camera.setAttribute('capture','environment');cameraLabel.append(camera);form.append(cameraLabel);
   const fileLabel=el('label','Ou choisir une photo / un PDF (10 Mo maximum)');const input=el('input');input.type='file';input.accept='.pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png';fileLabel.append(input);form.append(fileLabel);
   let selected=null,prepared=null;
   const chosen=el('p','Aucun fichier sélectionné.','muted');
   camera.onchange=()=>{selected=camera.files[0]||null;input.value='';prepared=null;chosen.textContent=selected?.name||'Aucun fichier sélectionné.';};
   input.onchange=()=>{selected=input.files[0]||null;camera.value='';prepared=null;chosen.textContent=selected?.name||'Aucun fichier sélectionné.';};
   const send=el('button','Partager avec le donneur d’ordre','btn primary');send.type='submit';form.append(chosen,el('p','Les pièces restent privées entre les parties et l’administration. Une photo ne remplace pas une lettre de voiture signée.','muted'),send);details.append(form);host.append(details);
   form.onsubmit=async e=>{
    e.preventDefault();if(send.disabled)return;if(!navigator.onLine){show('Connexion internet nécessaire pour transmettre le fichier. Aucun envoi effectué.',true);return;}
    const file=selected;const type=kind.value;const text=caption.value.trim();
    if(!file){show('Prenez une photo ou choisissez un fichier.',true);return;}
    const ext={'image/jpeg':'jpg','image/png':'png','application/pdf':'pdf'}[file.type];
    if(!ext||!file.size||file.size>10485760){show('Choisissez un fichier PDF, JPG ou PNG non vide de 10 Mo maximum.',true);return;}
    if(type==='reservation'&&text.length<10){show('Décrivez précisément les réserves (10 caractères minimum).',true);return;}
    if(prepared&&(prepared.file!==file||prepared.kind!==type||prepared.caption!==text))prepared=null;
    if(!prepared){const id=crypto.randomUUID();prepared={id,path:shipment.id+'/'+id+'.'+ext,file,kind:type,caption:text,uploaded:false};}
    const job=prepared;const controls=[...form.querySelectorAll('input,select,textarea,button')];controls.forEach(c=>c.disabled=true);busy++;show('Transmission de la pièce en cours…');
    try{
     await sameUser(userId);
     if(window.urgentDocumentAssistant){const check=await window.urgentDocumentAssistant.inspectFile(file,{kind:'registration'});if(!check.ok)throw Error(check.message);}
     if(!job.uploaded){const r=await timed(sb.storage.from(bucket).upload(job.path,file,{contentType:file.type,upsert:false}));if(r.error&&Number(r.error.statusCode)!==409)throw r.error;job.uploaded=true;}
     if(!valid())return;await sameUser(userId);
     const id=await rpc('urgent_add_mission_file',{p_shipment:shipment.id,p_file:job.id,p_kind:job.kind,p_caption:job.caption,p_filename:file.name,p_path:job.path});
     if(id!==job.id)throw Error('L’enregistrement du fichier ne peut pas être confirmé.');if(!valid())return;
     prepared=null;selected=null;form.reset();chosen.textContent='Aucun fichier sélectionné.';await load();show(type==='reservation'?'Photo et réserves enregistrées. Un signalement reste à traiter avec l’administration.':'Pièce partagée dans le dossier privé du donneur d’ordre.');
    }catch(e){show('Partage non confirmé : '+e.message+' Votre sélection est conservée pour réessayer.',true);}finally{busy--;controls.forEach(c=>c.disabled=false);}
   };
  })().catch(e=>show('Les documents de la course ne peuvent pas être chargés : '+e.message,true));
 }
 sb?.auth.onAuthStateChange((event,session)=>{if(event==='TOKEN_REFRESHED'||event==='SIGNED_IN'&&session?.user?.id===sessionUserId)return;sessionUserId=session?.user?.id||null;generation++;policyPromise=null;document.querySelectorAll('.mission-tools').forEach(e=>e.remove());});
 window.urgentMissionFiles={attach,get busy(){return busy>0;}};
})();
