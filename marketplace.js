'use strict';
(()=>{
 if(window.URGENT_MARKETPLACE_PILOT!==true)return;
 const $=id=>document.getElementById(id);
 const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const state={user:null,profile:null,shipments:[],offers:[],private:[],events:[],incidents:[],generation:0};
 const labels={published:'Course publiée',offer_submitted:'Offre enregistrée',offer_withdrawn:'Offre retirée',assigned_pilot_no_charge:'Attribution pilote gratuite',incident_reported:'Incident signalé',incident_resolved:'Signalement clôturé',open:'Ouverte',assigned:'Attribuée',heading_pickup:'En route vers l’enlèvement',at_pickup:'Arrivé au chargement',loaded:'Marchandise chargée',delivery_reported:'Livraison déclarée — confirmation client attendue',completed:'Réalisation confirmée par le client',cancelled:'Annulée'};
 const next={assigned:'heading_pickup',heading_pickup:'at_pickup',at_pickup:'loaded',loaded:'delivery_reported'};
 const notice=(id,text)=>{$(id).hidden=false;$(id).textContent=text;};
 const money=v=>new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(Number(v));
 const date=v=>new Date(v).toLocaleString('fr-FR',{timeZone:'Europe/Paris'});
 const reset=()=>{if($('pilotDirectory'))$('pilotDirectory').replaceChildren();state.generation++;state.shipments=[];state.offers=[];state.private=[];state.events=[];state.incidents=[];state.user=null;state.profile=null;$('shipmentForm').querySelectorAll('input,select,textarea,button').forEach(e=>e.disabled=true);$('shipments').replaceChildren();$('shipmentTracking').replaceChildren();};
 async function rpc(name,args){if(!sb)throw Error('Service de connexion indisponible.');const result=await sb.rpc(name,args);if(result.error)throw result.error;return result.data;}
 function button(text,action,cls='btn secondary'){
  const b=make('button',text,cls);b.type='button';b.onclick=async()=>{b.disabled=true;try{await action();}catch(e){notice('trackingNotice','Opération non confirmée : '+e.message);}finally{b.disabled=false;}};return b;
 }
 async function refresh(){
  reset();const generation=state.generation;
  try{
   if(!sb)throw Error('Service de connexion indisponible.');
   const current=await sb.auth.getUser();if(current.error)throw current.error;
   if(!current.data?.user){notice('courseCount','Connectez-vous avec votre compte professionnel pour consulter le pilote.');return;}
   const profile=await sb.from('profiles').select('id,role,company_id').eq('id',current.data.user.id).single();if(profile.error)throw profile.error;
   const results=await Promise.all([
    sb.from('urgent_shipments').select('*').order('created_at',{ascending:false}).limit(100),
    sb.from('urgent_offers').select('*').order('created_at',{ascending:false}).limit(500),
    sb.from('urgent_shipment_private').select('*').limit(100),
    sb.from('urgent_shipment_events').select('*').order('created_at',{ascending:false}).limit(300),
    sb.from('urgent_shipment_incidents').select('*').order('created_at',{ascending:false}).limit(300)
   ]);
   if(generation!==state.generation)return;
   for(const result of results)if(result.error)throw result.error;
   state.user=current.data.user;state.profile=profile.data;
   const canPublish=['client','admin'].includes(profile.data.role);
   $('testShipmentChoice').hidden=profile.data.role!=='admin';
   $('shipmentForm').querySelectorAll('input,select,textarea,button').forEach(e=>e.disabled=!canPublish);
   if(!canPublish)notice('formNotice','Ce compte est transporteur. Les demandes sont déposées par un compte donneur d’ordre distinct.');
   [state.shipments,state.offers,state.private,state.events,state.incidents]=results.map(r=>r.data||[]);
   $('pilotAdmin').hidden=profile.data.role!=='admin';render();
  }catch(e){if(generation===state.generation){reset();notice('courseCount','Pilote inaccessible : '+e.message+' Aucune donnée locale n’est publiée automatiquement.');}}
 }
 function render(){
  const list=$('shipments');list.replaceChildren();const query=$('courseSearch').value.trim().toLocaleLowerCase('fr');const vehicle=$('courseVehicle').value;
  const visible=state.shipments.filter(s=>s.status==='open'&&(!vehicle||s.vehicle===vehicle)&&(!query||`${s.origin} ${s.destination}`.toLocaleLowerCase('fr').includes(query)));
  notice('courseCount',`${visible.length} course(s) ouverte(s) affichée(s). Pilote gratuit, 100 courses maximum par chargement.`);
  for(const s of visible){
   const card=make('article',undefined,'shipment');const info=make('div');if(s.is_test)info.append(make('strong','EXERCICE FICTIF — AUCUN TRANSPORT RÉEL','test-badge'));info.append(make('h3',`${s.origin} → ${s.destination}`),make('p',`${date(s.pickup)} · ${s.vehicle} · ${s.pallets} palette(s) · ${s.weight} kg`));card.append(info);
   if(state.profile?.role==='carrier'&&s.owner_company_id!==state.profile.company_id){
    const existing=state.offers.find(o=>o.shipment_id===s.id&&o.carrier_company_id===state.profile.company_id);
    if(existing)info.append(make('p',`Votre proposition : ${money(existing.amount_ht)} HT · ${existing.status==='withdrawn'?'retirée':'enregistrée'}`));
    const form=make('form',undefined,'offer-pilot-form');const label=make('label',s.is_test?'Tarif fictif de test (€ HT)':'Votre tarif HT à recevoir (€)');const input=make('input');input.type='number';input.min='0.01';input.max='1000000';input.step='0.01';input.required=true;input.value=existing?.amount_ht||'';label.append(input);const submit=make('button','Enregistrer mon offre confidentielle','btn primary');submit.type='submit';form.append(label,submit);
    form.onsubmit=async event=>{event.preventDefault();if(!form.reportValidity())return;submit.disabled=true;try{await rpc('urgent_submit_offer',{p_shipment:s.id,p_amount:input.value});await refresh();notice('trackingNotice','Offre enregistrée. Les autres transporteurs ne peuvent pas consulter votre prix.');}catch(e){notice('trackingNotice','Offre refusée : '+e.message);}finally{submit.disabled=false;}};
    card.append(form);
    if(existing?.status==='submitted')card.append(button('Retirer mon offre',async()=>{if(!confirm('Retirer cette proposition ?'))return;await rpc('urgent_withdraw_offer',{p_offer:existing.id});await refresh();}));
   }list.append(card);
  }
  if(!visible.length)list.append(make('p','Aucune course ouverte ne correspond à la recherche.'));
  renderTracking();
 }
 function incidentForm(text,action){
  const details=make('details');details.append(make('summary',text));const form=make('form',undefined,'incident-form');const label=make('label','Description (10 à 2000 caractères)');const input=make('textarea');input.minLength=10;input.maxLength=2000;input.required=true;label.append(input);const submit=make('button',text,'btn secondary');submit.type='submit';form.append(label,submit);
  form.onsubmit=async e=>{e.preventDefault();if(!form.reportValidity())return;submit.disabled=true;try{await action(input.value.trim());}catch(error){notice('trackingNotice','Signalement non confirmé : '+error.message);}finally{submit.disabled=false;}};details.append(form);return details;
 }
 function renderTracking(){
  const host=$('shipmentTracking');host.replaceChildren();const company=state.profile?.company_id;
  const rows=state.shipments.filter(s=>s.owner_company_id===company||s.assigned_company_id===company||state.profile?.role==='admin');
  for(const s of rows){
   const card=make('article',undefined,'dossier');if(s.is_test)card.append(make('strong','EXERCICE FICTIF — AUCUN TRANSPORT RÉEL','test-badge'));card.append(make('h3',`${s.origin} → ${s.destination}`),make('p',`${labels[s.status]} · ${s.id}`));
   const contact=state.private.find(p=>p.shipment_id===s.id);if(contact){card.append(make('p',`Contact donneur d’ordre : ${contact.company_name} · ${contact.contact_email}`));if(contact.instructions)card.append(make('p',contact.instructions));}
   if(s.owner_company_id===company&&s.status==='open'){
    const offers=state.offers.filter(o=>o.shipment_id===s.id&&o.status==='submitted');
    card.append(make('p',`${offers.length} proposition(s) active(s)`));
    for(const offer of offers){const box=make('div',undefined,'doc-item');box.append(make('p',`${money(offer.amount_ht)} HT — transporteur ${offer.carrier_company_id}`));box.append(make('p',`Frais indicatifs de 1,5 % : ${money(Number(offer.amount_ht)*0.015)} HT. Pilote gratuit : aucun frais encaissé ni facturé.`));box.append(button('Sélectionner pour le pilote gratuit',async()=>{if(!confirm(`Attribuer au tarif de ${money(offer.amount_ht)} HT ? Pilote gratuit : aucun encaissement, aucune facturation automatique. Le contrat de transport reste à confirmer directement entre les parties.`))return;await rpc('urgent_accept_offer',{p_offer:offer.id,p_pilot_ack:true,p_expected_amount:offer.amount_ht});await refresh();}));card.append(box);}
    card.append(button('Annuler la course non attribuée',async()=>{if(!confirm('Annuler cette course ?'))return;await rpc('urgent_cancel_shipment',{p_shipment:s.id});await refresh();}));
   }
   if(s.assigned_company_id===company&&next[s.status])card.append(button(labels[next[s.status]],async()=>{if(!confirm('Confirmer : '+labels[next[s.status]]+' ?'))return;await rpc('urgent_progress_shipment',{p_shipment:s.id,p_next:next[s.status]});await refresh();}));
   if(s.owner_company_id===company&&s.status==='delivery_reported')card.append(button('Confirmer la réalisation',async()=>{if(!confirm('Confirmez uniquement si vous avez vérifié la réalisation de la prestation.'))return;await rpc('urgent_progress_shipment',{p_shipment:s.id,p_next:'completed'});await refresh();}));
   if(s.accepted_offer_id)card.append(button('Voir la fiche d’attribution pilote',async()=>{
    const detail=await rpc('urgent_assignment_details',{p_shipment:s.id});const existing=card.querySelector('.assignment-detail');if(existing)existing.remove();const area=make('div',undefined,'doc-item assignment-detail');area.append(make('p',`Transporteur : ${detail.carrier_company} · ${detail.carrier_email}`),make('p',`Tarif transport convenu : ${money(detail.amount_ht)} HT. Frais plateforme encaissés : 0 €. Attribution le ${date(detail.assigned_at)}.`),make('p','Fiche pilote, sans facture ni confirmation d’affrètement automatique. Les parties doivent confirmer directement leur contrat de transport.'));card.append(area);
   }));
   if(s.accepted_offer_id){
    const incidents=state.incidents.filter(i=>i.shipment_id===s.id);
    const area=make('section',undefined,'shipment-incidents');area.append(make('h4','Signalements de prestation'));
    for(const incident of incidents){const box=make('div',undefined,'doc-item');box.append(make('strong',incident.status==='open'?'Signalement ouvert':'Signalement clôturé'),make('p',incident.description));if(incident.resolution)box.append(make('p','Traitement : '+incident.resolution));
     if(incident.status==='open'&&state.profile?.role==='admin')box.append(incidentForm('Décrire le traitement puis clôturer',async value=>{await rpc('urgent_resolve_incident',{p_incident:incident.id,p_resolution:value});await refresh();}));area.append(box);
    }
    if(!incidents.some(i=>i.status==='open'&&i.reported_by===state.user.id))area.append(incidentForm('Signaler un retard ou un problème',async value=>{await rpc('urgent_report_incident',{p_shipment:s.id,p_description:value});await refresh();}));
    else area.append(make('p','Votre signalement est ouvert. Sa clôture nécessite une intervention de 13 URGENT.'));
    area.append(make('p','Ces signalements restent privés entre les parties et l’administration. Ils ne constituent ni une décision de remboursement ni une preuve de livraison.','muted'));card.append(area);
   }
   const events=state.events.filter(e=>e.shipment_id===s.id).slice().reverse();if(events.length){const details=make('details');details.append(make('summary','Historique horodaté'));for(const e of events)details.append(make('p',`${date(e.created_at)} · ${labels[e.event_type]||e.event_type}`));card.append(details);}
   host.append(card);
  }
  if(!rows.length)host.append(make('p','Aucune course suivie pour ce compte.'));
 }
 $('shipmentForm').onsubmit=async event=>{
  event.preventDefault();const form=event.currentTarget;if(!form.reportValidity())return;const button=event.submitter;button.disabled=true;
  try{const isTest=$('testShipmentInput').checked&&state.profile?.role==='admin';const f=new FormData(form);await rpc($('testShipmentInput').checked&&state.profile?.role==='admin'?'urgent_publish_test_shipment':'urgent_publish_shipment',{p_origin:String(f.get('origin')).trim(),p_destination:String(f.get('destination')).trim(),p_pickup:new Date(String(f.get('pickup'))).toISOString(),p_vehicle:f.get('vehicle'),p_pallets:Number(f.get('pallets')),p_weight:Number(f.get('weight')),p_company_name:String(f.get('company')).trim(),p_email:String(f.get('email')).trim(),p_instructions:String(f.get('notes')).trim()});form.reset();await refresh();notice('formNotice',isTest?'Exercice fictif publié. Aucun transport réel ni paiement.':'Course publiée dans le pilote gratuit. Les coordonnées et instructions privées ne sont accessibles qu’aux parties après attribution.');}catch(e){notice('formNotice','Publication refusée : '+e.message);}finally{button.disabled=false;}
 };
 async function renderPilotDirectory(){
  const generation=state.generation;
  const host=$('pilotDirectory');host.replaceChildren();
  try{const rows=await rpc('urgent_pilot_directory',{});
   if(generation!==state.generation||state.profile?.role!=='admin')return;
   for(const row of rows){const card=make('div',undefined,'doc-item');card.append(make('strong',`${row.company_name} · ${row.account_role==='carrier'?'transporteur':'donneur d’ordre'}`),make('span',`SIRET déclaré à contrôler : ${row.declared_siret||'non fourni'} · Pilote : ${row.pilot_enabled?'autorisé':'non autorisé'} · Dossier transporteur : ${row.carrier_ready?'admissible au pilote':'non admissible ou sans objet'}`));
    if(row.account_role==='carrier')card.append(button('Voir les pièces qui bloquent',async()=>{
      const generation=state.generation;const rows=await rpc('urgent_document_checklist',{p_company:row.company_id});if(generation!==state.generation)return;
      card.querySelector('.document-checklist')?.remove();const list=make('ul',undefined,'document-checklist');
      const names={registration:'Kbis / immatriculation',transport_licence:'Licence',insurance_rc:'Assurance RC',insurance_goods:'Assurance marchandises'};
      const reasons={missing:'pièce manquante',not_approved:'en attente ou refusée',expiry_missing:'date de validité manquante',expired:'pièce expirée',valid:'pièce approuvée et date valide'};
      for(const item of rows)list.append(make('li',`${names[item.document_type]||item.document_type} : ${reasons[item.reason]||item.reason}${item.expires_on?' — échéance '+item.expires_on:''}`));card.append(list);
    }));
    card.append(button('Préparer la décision pour cet établissement',async()=>{const form=$('pilotAccessForm');form.elements.companyId.value=row.company_id;form.elements.siret.value=row.declared_siret||'';form.elements.plan.value=row.pilot_plan||row.requested_plan||'basics';form.elements.registryChecked.checked=false;form.elements.enabled.value=row.pilot_enabled?'false':'true';form.scrollIntoView({block:'center'});}));host.append(card);
   }
  }catch(e){notice('pilotAccessNotice','Annuaire pilote indisponible : '+e.message);}
 }
 const pilotDirectory=make('div');pilotDirectory.id='pilotDirectory';$('pilotAccessForm').before(pilotDirectory);
 $('openAdmin').addEventListener('click',async()=>{
  if(!state.profile)await refresh();
  if(state.profile?.role==='admin')await renderPilotDirectory();
 });
 $('pilotAccessForm').onsubmit=async event=>{
  event.preventDefault();const b=event.submitter;b.disabled=true;const f=new FormData(event.currentTarget);
  try{await rpc('urgent_review_pilot',{p_company:f.get('companyId'),p_siret:f.get('siret'),p_plan:f.get('plan'),p_enabled:f.get('enabled')==='true',p_registry_checked:f.get('registryChecked')==='on'});await renderPilotDirectory();notice('pilotAccessNotice','Décision pilote enregistrée. Aucun abonnement payé activé. Les documents sont contrôlés à chaque offre et attribution.');}catch(e){notice('pilotAccessNotice','Décision refusée : '+e.message);}finally{b.disabled=false;}
 };
 $('courseFilters').onsubmit=e=>e.preventDefault();$('courseSearch').oninput=render;$('courseVehicle').onchange=render;
 $('exportShipments').textContent='Exporter les anciennes demandes locales';
 $('exportShipments').onclick=()=>{const raw=localStorage.getItem('13urgent_demo_shipments_v1')||'[]';const url=URL.createObjectURL(new Blob([raw],{type:'application/json'}));const a=make('a');a.href=url;a.download='13urgent-anciennes-demandes-locales.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 const testChoice=make('label',undefined,'professional-check wide');testChoice.id='testShipmentChoice';testChoice.hidden=true;
 const testInput=make('input');testInput.type='checkbox';testInput.id='testShipmentInput';testChoice.append(testInput,make('span','Créer un exercice fictif sans transport réel (administrateur uniquement).'));
 $('shipmentForm').prepend(testChoice);
 const shipmentSiret=$('shipmentForm').elements.siret;shipmentSiret.required=false;shipmentSiret.closest('label').hidden=true;
 const refreshButton=button('Actualiser les courses et le suivi',refresh);$('courseFilters').after(refreshButton);
 const banner=make('p','Pilote professionnel gratuit — aucun paiement, abonnement payé ou frais de mise en relation activé.','pilot-banner');document.querySelector('main').prepend(banner);
 document.querySelector('.hero-inner>p').textContent='Pilote réservé aux professionnels vérifiés : publiez une course, comparez les propositions confidentielles et suivez la prestation. Aucun paiement sur ce pilote.';
 document.querySelector('#courses .section-head p').textContent='Courses partagées du pilote professionnel gratuit. Les prix proposés sont confidentiels entre chaque transporteur, le donneur d’ordre et l’administration.';
 document.querySelector('#deposer .section-head p').textContent='Pilote gratuit : connexion et établissement préalablement vérifié par 13 URGENT requis. Les offres sont réservées aux transporteurs autorisés et aux documents valides.';
 document.querySelector('#suivi h2').textContent='Mes courses et leur suivi';document.querySelector('#suivi .section-head p').textContent='Suivi partagé entre les parties. La livraison déclarée par le transporteur doit être confirmée par le donneur d’ordre ; aucune preuve de livraison signée n’est encore collectée ici.';
 document.querySelector('#suivi .eyebrow').textContent='PILOTE PROFESSIONNEL GRATUIT';document.querySelector('nav a[href="#suivi"]').textContent='Mes courses';
 sb?.auth.onAuthStateChange(()=>{reset();$('pilotAdmin').hidden=true;setTimeout(refresh,0);});refresh();
})();
