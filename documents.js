"use strict";
// Les actions utilisent exclusivement la session utilisateur et les politiques Supabase.
const DOC_BUCKET='carrier-documents';
const adminPage=document.body.dataset.adminPage==='true';
const documentLabels={registration:'Immatriculation / Kbis',transport_licence:'Licence de transport',insurance_rc:'Assurance responsabilité civile',insurance_goods:'Assurance marchandises transportées',other:'Autre document'};
const documentLabel=kind=>documentLabels[kind]||kind;
const doc$=id=>document.getElementById(id);
function docMsg(id,message){const e=doc$(id)||doc$('authNotice');if(e){e.hidden=false;e.textContent=message;}}
function safeText(v){return String(v??'');}
function line(parent,tag,txt,cls){const e=document.createElement(tag);if(cls)e.className=cls;e.textContent=safeText(txt);parent.append(e);return e;}
const documentCameraLabel=document.createElement('label');documentCameraLabel.className='wide';documentCameraLabel.textContent='Ou prendre le justificatif en photo avec le téléphone';
const documentCamera=document.createElement('input');documentCamera.id='documentCamera';documentCamera.type='file';documentCamera.accept='image/jpeg,image/png';documentCamera.setAttribute('capture','environment');documentCameraLabel.append(documentCamera);doc$('documentFile').closest('label').after(documentCameraLabel);
documentCamera.onchange=()=>{doc$('documentFile').value='';doc$('documentFile').required=!documentCamera.files.length;};
doc$('documentFile').addEventListener('change',()=>{documentCamera.value='';doc$('documentFile').required=true;});
let professionalProfile=null;
let professionalAccessGeneration=0;
let professionalSessionId=null;
let clientDocumentUploadAvailable=false;
async function refreshProfessionalAccess(){
  const generation=++professionalAccessGeneration;
  doc$('openDocuments').hidden=true;doc$('openAdmin').hidden=true;professionalProfile=null;clientDocumentUploadAvailable=false;
  if(!sb)return;
  const {data:{user},error:ue}=await sb.auth.getUser();
  if(generation!==professionalAccessGeneration)return;
  const id=user?.id||null;
  if(id!==professionalSessionId){professionalSessionId=id;clearProfessionalViews();}
  if(ue||!user)return;
  const {data,error}=await sb.from('profiles').select('id,company_id,role').eq('id',user.id).maybeSingle();
  if(generation!==professionalAccessGeneration)return;
  if(error){console.warn('Profil non accessible',error.message);return;}
  professionalProfile=data;
  if(data?.role==='client'&&typeof sb.rpc==='function'){try{const policy=await sb.rpc('urgent_document_alert_policy',{});if(generation!==professionalAccessGeneration)return;clientDocumentUploadAvailable=!policy.error&&policy.data?.client_upload===true;}catch{}}
  doc$('openDocuments').hidden=data?.role!=='carrier'&&!(data?.role==='client'&&clientDocumentUploadAvailable);
  doc$('openAdmin').hidden=data?.role!=='admin';
  if(doc$('adminPageNotice'))doc$('adminPageNotice').textContent=data?.role==='admin'?'Administration : ouvrez les dossiers ou gérez les abonnements et frais ci-dessous.':'Accès réservé aux administrateurs. Vous pouvez revenir à l’accueil.';
}
window.refreshProfessionalAccess=refreshProfessionalAccess;
async function getOwnCompany(){
  if(!professionalProfile?.company_id)throw Error('Profil entreprise introuvable. Reconnectez-vous.');
  const {data,error}=await sb.from('companies').select('id,name,verification_status').eq('id',professionalProfile.company_id).single();
  if(error)throw error;return data;
}
async function showMyDocuments(){
  const generation=professionalAccessGeneration;
  doc$('documentNotice').hidden=true;
  if(!professionalProfile||!(professionalProfile.role==='carrier'||professionalProfile.role==='client'&&clientDocumentUploadAvailable))return;
  const clientOnly=professionalProfile.role==='client';const dialog=doc$('documentsDialog');
  renewalWarning.hidden=clientOnly;
  dialog.querySelector('.eyebrow').textContent=clientOnly?'ESPACE DONNEUR D’ORDRE':'ESPACE TRANSPORTEUR';
  dialog.querySelector('h2+p').textContent=clientOnly?'Vous pouvez transmettre votre extrait Kbis ou justificatif d’immatriculation à l’administration. Ce dépôt ne valide pas automatiquement votre établissement.':'Les missions restent visibles. Aucune proposition ne sera autorisée avant la validation de votre dossier par 13 URGENT.';
  for(const option of doc$('documentType').options){option.hidden=clientOnly&&option.value!=='registration';option.disabled=option.hidden;}
  if(clientOnly)doc$('documentType').value='registration';
  doc$('documentsDialog').showModal();
  try{
    const c=await getOwnCompany();if(generation!==professionalAccessGeneration)return;doc$('companyStatus').textContent=`${c.name} — Dossier : ${c.verification_status}`;
    const {data,error}=await sb.from('carrier_documents').select('id,document_type,original_filename,review_status,expires_on,created_at').eq('company_id',c.id).order('created_at',{ascending:false});
    if(error)throw error;
    if(generation!==professionalAccessGeneration)return;
    const host=doc$('myDocuments');host.replaceChildren();
    if(!data?.length)line(host,'p','Aucun justificatif envoyé.');
    for(const d of data){const item=line(host,'div','', 'doc-item');line(item,'strong',d.original_filename||d.document_type);line(item,'span',`${documentLabel(d.document_type)} · ${d.review_status}${d.expires_on?' · expire le '+d.expires_on:''}`);if(!clientOnly&&window.urgentDossiers){const due=window.urgentDossiers.renewalDate(d.created_at);line(item,'span',due?'Actualisation semestrielle avant le '+due:'Date de dépôt à vérifier auprès de l’administration.');}if(window.urgentSupport){const help=line(item,'button','Demander une préanalyse','btn secondary');help.type='button';help.onclick=()=>window.urgentSupport.reviewDocument(d.id);}}
    if(!clientOnly&&typeof sb.rpc==='function'&&window.urgentDocumentAssistant){try{const checklist=await sb.rpc('urgent_document_checklist',{p_company:c.id});if(generation!==professionalAccessGeneration)return;if(!checklist.error&&Array.isArray(checklist.data)){const report=window.urgentDocumentAssistant.analyseChecklist(checklist.data);const panel=line(host,'div',report.message,'support-file-report');for(const item of report.items)line(panel,'p',item.label+' : '+item.message);}}catch{/* Le diagnostic ne bloque pas l’accès aux pièces. */}}
  }catch(e){if(generation===professionalAccessGeneration)docMsg('documentNotice','Erreur : '+e.message);}
}
async function uploadDocument(e){
  e.preventDefault();const btn=e.submitter;const generation=professionalAccessGeneration;btn.disabled=true;doc$('documentNotice').hidden=true;
  try{
    if(!(professionalProfile?.role==='carrier'||professionalProfile?.role==='client'&&clientDocumentUploadAvailable))throw Error('Connectez-vous avec un compte professionnel autorisé.');
    const company=await getOwnCompany();if(generation!==professionalAccessGeneration)return;const file=documentCamera.files[0]||doc$('documentFile').files[0];
    if(!file)throw Error('Choisissez un fichier.');
    if(file.size>10*1024*1024)throw Error('Le fichier dépasse 10 Mo.');
    const allowed={'application/pdf':'pdf','image/jpeg':'jpg','image/png':'png'};
    if(!allowed[file.type])throw Error('Formats autorisés : PDF, JPG et PNG.');
    const kind=doc$('documentType').value;const expiry=doc$('documentExpiry').value;
    if(professionalProfile.role==='client'&&kind!=='registration')throw Error('Un donneur d’ordre peut transmettre son justificatif d’immatriculation.');
    if(kind!=='registration'&&!expiry)throw Error('Renseignez la date de fin de validité figurant sur la licence ou l’assurance.');
    if(!['registration','transport_licence','insurance_rc','insurance_goods'].includes(kind))throw Error('Catégorie de document non prise en charge.');
    if(window.urgentDocumentAssistant){const inspection=await window.urgentDocumentAssistant.inspectFile(file,{kind,expiry});if(generation!==professionalAccessGeneration)return;if(!inspection.ok)throw Error(inspection.message);}
    const path=`${company.id}/${crypto.randomUUID()}.${allowed[file.type]}`;
    const {error:uploadError}=await sb.storage.from(DOC_BUCKET).upload(path,file,{contentType:file.type,upsert:false});
    if(generation!==professionalAccessGeneration)return;
    if(uploadError)throw uploadError;
    const row={company_id:company.id,document_type:kind,storage_path:path,original_filename:file.name,review_status:'pending'};
    if(expiry)row.expires_on=expiry;
    const {error}=await sb.from('carrier_documents').insert(row);
    if(generation!==professionalAccessGeneration)return;
    if(error)throw Error('Fichier envoyé mais fiche non enregistrée : '+error.message+' (contactez 13 URGENT).');
    doc$('documentFile').value='';documentCamera.value='';doc$('documentFile').required=true;await showMyDocuments();if(generation!==professionalAccessGeneration)return;docMsg('documentNotice',`Document envoyé dans la catégorie « ${documentLabel(kind)} ». Il reste en attente de vérification par 13 URGENT.`);
  }catch(err){if(generation===professionalAccessGeneration)docMsg('documentNotice','Envoi impossible : '+err.message);}finally{btn.disabled=false;}
}
async function showAdmin(){
  if(!adminPage||professionalProfile?.role!=='admin')return;
  doc$('adminDialog').showModal();await loadAdmin();
}
async function loadAdmin(){
  if(!adminPage||professionalProfile?.role!=='admin')return;
  const generation=professionalAccessGeneration;
  doc$('adminNotice').hidden=true;const host=doc$('adminDossiers');host.replaceChildren();line(host,'p','Chargement des dossiers…');
  async function readAll(table,columns,filter,sort='created_at',tie='id'){
    const query=()=>{let q=sb.from(table).select(columns);if(filter)q=q.in('company_type',filter);return q.order(sort,{ascending:false});};
    const first=query();if(typeof first.range!=='function')return await first;
    const rows=[];for(let offset=0;;offset+=200){const result=await query().order(tie).range(offset,offset+199);if(generation!==professionalAccessGeneration)return{data:[]};if(result.error)return result;rows.push(...result.data||[]);if((result.data||[]).length<200)return{data:rows};}
  }
  const [companies,docs,decisions]=await Promise.all([
    readAll('companies','id,name,company_type,verification_status',['carrier','both','client']),
    readAll('carrier_documents','id,company_id,document_type,storage_path,original_filename,review_status,expires_on,created_at'),
    readAll('urgent_business_access','company_id,pilot_enabled,reviewed_at',null,'company_id','company_id')
  ]);
  if(generation!==professionalAccessGeneration)return;
  if(companies.error||docs.error){docMsg('adminNotice','Lecture impossible : '+(companies.error?.message||docs.error?.message));host.replaceChildren();return;}
  let directory=[];try{if(typeof sb.rpc==='function'){const r=await sb.rpc('urgent_pilot_directory',{});if(!r.error&&Array.isArray(r.data))directory=r.data;}}catch{}
  if(generation!==professionalAccessGeneration)return;
  host.replaceChildren();if(!companies.data?.length){line(host,'p','Aucun établissement enregistré.');return;}
  const folders=window.urgentDossiers?.folders(host,[['review','Nouveaux documents à examiner'],['renew','Dossiers à compléter ou à actualiser'],['validated','Dossiers documentaires validés'],['refused','Inscriptions refusées / accès suspendus']]);
  for(const c of companies.data){
    const companyDocs=(docs.data||[]).filter(d=>d.company_id===c.id);const access=directory.find(row=>row.company_id===c.id);const clientOnly=c.company_type==='client'&&access?.account_role!=='carrier';
    const clientLatest=window.urgentDossiers?.latestDocuments(companyDocs).find(d=>d.document_type==='registration')||companyDocs.find(d=>d.document_type==='registration');
    const refused=!decisions.error&&(decisions.data||[]).some(d=>d.company_id===c.id&&d.pilot_enabled===false&&d.reviewed_at);
    const folder=refused?'refused':clientOnly?(!clientLatest||clientLatest.review_status!=='approved'?'review':clientLatest.expires_on&&clientLatest.expires_on<new Date().toISOString().slice(0,10)?'renew':'validated'):window.urgentDossiers?.classify(companyDocs)||'review';
    const card=line(folders?.containers[folder]||host,'article','', 'dossier');line(card,'h3',c.name);line(card,'p',`Référence entreprise : ${c.id}`);
    line(card,'p',refused?'Inscription refusée / accès de l’établissement suspendu.':access?`Autorisation de l’établissement : ${access.pilot_enabled?'accordée':'à valider ou suspendue'}`+(clientOnly?' · Donneur d’ordre':` · Dossier et droits transporteur : ${access.carrier_ready?'valides':'à compléter / vérifier'}`):'Autorisation de l’établissement : état non confirmé, consultez la validation des établissements.');
    const kinds=clientOnly?['registration']:['registration','transport_licence','insurance_rc','insurance_goods'];const missing=kinds.filter(kind=>!companyDocs.some(d=>d.document_type===kind));if(missing.length)line(card,'p',clientOnly?'Justificatif d’immatriculation non déposé.':'Catégories manquantes : '+missing.map(documentLabel).join(', ')+'.',clientOnly?'muted':'danger');
    const prepare=line(card,'button','Préparer la validation de cet établissement','btn secondary');prepare.type='button';prepare.onclick=async()=>{prepare.disabled=true;try{if(window.urgentPrepareBusinessReview)await window.urgentPrepareBusinessReview(c.id);else docMsg('adminNotice','Ouvrez la validation des établissements dans l’administration.');}catch(e){docMsg('adminNotice','Préparation impossible : '+e.message);doc$('adminNotice').scrollIntoView({block:'nearest'});}finally{prepare.disabled=false;}};
    const refuse=line(card,'button',refused?'Maintenir le refus / la suspension':'Refuser l’inscription / suspendre l’accès','btn primary');refuse.type='button';
    const refusalNotice=line(card,'p','');refusalNotice.setAttribute('role','status');
    refuse.onclick=async()=>{
      if(!confirm('Refuser l’inscription de « '+c.name+' » et bloquer la publication ainsi que les nouvelles offres ? Le dossier et son historique seront conservés.'))return;
      const actorId=professionalProfile?.id;refuse.disabled=true;refusalNotice.textContent='Enregistrement du refus…';
      try{
        const {data:auth,error:authError}=await sb.auth.getUser();
        if(generation!==professionalAccessGeneration)return;
        if(authError||!auth?.user||professionalProfile?.role!=='admin'||actorId!==auth.user.id)throw Error('Session administrateur expirée. Reconnectez-vous.');
        const current=await sb.from('urgent_business_access').select('siret,plan').eq('company_id',c.id).maybeSingle();if(current.error)throw current.error;
        if(generation!==professionalAccessGeneration)return;
        const siret=current.data?.siret||access?.declared_siret||'';
        if(!/^[0-9]{14}$/.test(siret))throw Error('SIRET absent ou incorrect. Renseignez-le dans la validation des établissements pour enregistrer la suspension.');
        const {error}=await sb.rpc('urgent_review_pilot',{p_company:c.id,p_siret:siret,p_plan:current.data?.plan||'basics',p_enabled:false,p_registry_checked:false});if(error)throw error;
        if(generation!==professionalAccessGeneration)return;
        refusalNotice.textContent='Refus enregistré. Actualisation du dossier…';
        await loadAdmin();if(generation!==professionalAccessGeneration)return;
        docMsg('adminNotice','Inscription de '+c.name+' refusée : publication et nouvelles offres bloquées. Dossier conservé dans « Inscriptions refusées / accès suspendus ». Aucun e-mail de refus n’a été envoyé.');doc$('adminNotice').scrollIntoView({block:'nearest'});
      }catch(e){if(generation===professionalAccessGeneration)refusalNotice.textContent='Refus non confirmé : '+e.message;}
      finally{refuse.disabled=false;}
    };
    if(!clientOnly&&access?.pilot_plan){const plans={basics:'Start gratuit',bronze:'Drive',silver:'Boost',gold:'Premium'};line(card,'p','Forfait retenu par l’administration : '+(plans[access.pilot_plan]||access.pilot_plan)+'. Les périodes payantes restent contrôlées séparément.');}
    if(!clientOnly&&access?.pilot_enabled&&window.urgentSupport?.notifyBusinessValidation){
      const notify=line(card,'button','Notifier la décision au transporteur','btn secondary');notify.type='button';const delivery=line(card,'p','');delivery.setAttribute('role','status');
      notify.onclick=async()=>{notify.disabled=true;delivery.textContent='Envoi de la notification en cours…';try{const mail=await window.urgentSupport.notifyBusinessValidation(c.id,true);if(generation!==professionalAccessGeneration)return;delivery.textContent=mail.notified?'Le service e-mail a accepté la notification'+(mail.recipient_emails?.length?' à '+mail.recipient_emails.join(', '):'')+'. '+(mail.eligible?'Dossier et droits transporteur valides.':'L’e-mail indique les éléments encore nécessaires avant les propositions.'):mail.notification_status==='service_update_required'?'La fonction support-assistant doit être mise à jour dans Supabase pour activer cet envoi.':'Notification non confirmée. La décision enregistrée reste inchangée.';}catch{delivery.textContent='Notification non confirmée. La décision enregistrée reste inchangée.';}finally{notify.disabled=false;delivery.scrollIntoView({block:'nearest'});}};
    }
    const items=(docs.data||[]).filter(d=>d.company_id===c.id);
    if(!items.length)line(card,'p','Aucun document déposé.');
    const latestIds=new Set((window.urgentDossiers?.latestDocuments(items)||items).map(d=>d.id));
    let oldVersions=null;if(items.some(d=>!latestIds.has(d.id))){oldVersions=document.createElement('details');line(oldVersions,'summary','Anciennes versions conservées ('+items.filter(d=>!latestIds.has(d.id)).length+')');card.append(oldVersions);}
    for(const d of items){
      const historical=!latestIds.has(d.id);const row=line(historical?oldVersions:card,'div','', 'doc-item');line(row,'strong',`${documentLabel(d.document_type)} — ${d.original_filename||'fichier'}`);
      line(row,'span',`Statut : ${d.review_status}${d.expires_on?' · Expiration : '+d.expires_on:''}`);
      if(!clientOnly&&window.urgentDossiers){const due=window.urgentDossiers.renewalDate(d.created_at);line(row,'span',due?'Actualisation semestrielle avant le '+due:'Date de dépôt à vérifier.');}
      const buttons=line(row,'div','', 'doc-actions');
      if(window.urgentSupport){const help=line(buttons,'button','Avis de l’assistant','btn secondary');help.type='button';help.onclick=()=>window.urgentSupport.reviewDocument(d.id);}
      const view=line(buttons,'button','Voir le fichier','btn secondary');view.type='button';view.onclick=async()=>{
        const {data,error}=await sb.storage.from(DOC_BUCKET).createSignedUrl(d.storage_path,60);
        if(error){docMsg('adminNotice','Fichier inaccessible : '+error.message);return;}
        window.open(data.signedUrl,'_blank','noopener,noreferrer');
      };
      if(historical)continue;
      const edit=line(buttons,'button','Corriger la catégorie / la date','btn secondary');edit.type='button';
      edit.onclick=()=>{
        if(row.querySelector('.document-correction'))return;
        const form=document.createElement('form');form.className='document-correction doc-form';
        const kindLabel=line(form,'label','Catégorie vérifiée');const select=document.createElement('select');
        for(const [value,label] of Object.entries(documentLabels)){const option=document.createElement('option');option.value=value;option.textContent=label;option.selected=d.document_type===value;select.append(option);}kindLabel.append(select);
        const dateLabel=line(form,'label','Date de fin de validité figurant sur la pièce');const expiry=document.createElement('input');expiry.type='date';expiry.value=d.expires_on||'';dateLabel.append(expiry);
        line(form,'p','Toute correction remet la pièce en attente de revue. Pour le pilote, la licence et les assurances nécessitent une date de validité renseignée.','wide muted');
        const submit=line(form,'button','Enregistrer la correction','btn primary');submit.type='submit';
        const cancel=line(form,'button','Fermer','btn secondary');cancel.type='button';cancel.onclick=()=>form.remove();
        form.onsubmit=async event=>{event.preventDefault();submit.disabled=true;
          try{const {error}=await sb.rpc('urgent_correct_document',{p_document:d.id,p_kind:select.value,p_expiry:expiry.value||null});if(error)throw error;
            await loadAdmin();docMsg('adminNotice','Correction enregistrée. La pièce doit être contrôlée puis approuvée à nouveau.');
          }catch(e){docMsg('adminNotice','Correction impossible : '+e.message);}finally{submit.disabled=false;}
        };row.append(form);
      };
      if(d.review_status==='pending'||d.review_status==='approved'){
        const decisions=d.review_status==='approved'?[['rejected','Retirer l’approbation']]:[['approved','Accepter'],['rejected','Refuser']];
        for(const [status,label] of decisions){
          const b=line(buttons,'button',label,status==='approved'?'btn primary':'btn secondary');b.type='button';
          b.onclick=async()=>{
            const question=d.review_status==='approved'?'Retirer l’approbation de ce document ? Le transporteur ne pourra plus faire de nouvelles propositions ni recevoir d’attribution tant que son dossier ne sera pas valide.':`${label} ce document ?`;
            if(!confirm(question))return;
            const actionGeneration=professionalAccessGeneration;
            b.disabled=true;
            try{
              const {data,error:authError}=await sb.auth.getUser();
              if(actionGeneration!==professionalAccessGeneration)return;
              if(authError||!data?.user||professionalProfile?.role!=='admin'||professionalProfile.id!==data.user.id)throw Error('Session administrateur expirée. Reconnectez-vous.');
              const {error}=await sb.from('carrier_documents').update({review_status:status,reviewed_at:new Date().toISOString(),reviewed_by:data.user.id}).eq('id',d.id).select('id').single();
              if(error)throw error;
              if(actionGeneration!==professionalAccessGeneration)return;
              await loadAdmin();
              if(actionGeneration!==professionalAccessGeneration)return;
              docMsg('adminNotice',d.review_status==='approved'?'Approbation retirée. Le dossier sera de nouveau contrôlé lors des prochaines propositions et attributions.':`Document ${status==='approved'?'accepté':'refusé'}. L’entreprise n’est pas automatiquement validée.`);
              if(status==='approved'&&window.urgentSupport?.notifyBusinessValidation){const mail=await window.urgentSupport.notifyBusinessValidation(c.id);if(actionGeneration!==professionalAccessGeneration)return;const detail=mail.notified?' Le service e-mail a accepté la notification de validation.':mail.notification_status==='not_ready'||mail.notification_status==='establishment_not_approved'?' Les accès ne sont pas encore tous validés ; aucun e-mail d’activation envoyé.':mail.notification_status==='service_update_required'?' La fonction d’envoi doit être mise à jour dans Supabase.':' L’envoi de l’e-mail n’est pas confirmé.';docMsg('adminNotice',doc$('adminNotice').textContent+detail);doc$('adminNotice').scrollIntoView({block:'nearest'});}
            }catch(e){if(actionGeneration===professionalAccessGeneration)docMsg('adminNotice','Validation impossible : '+e.message);}
            finally{b.disabled=false;}
          };
        }
      }
    }
  }
  folders?.update();
}
window.refreshAdminDossiers=loadAdmin;
doc$('openDocuments').addEventListener('click',()=>showMyDocuments().catch(()=>docMsg('documentNotice','Service momentanément inaccessible.')));
if(adminPage)doc$('openAdmin').addEventListener('click',event=>{event.preventDefault();showAdmin().catch(()=>docMsg('adminNotice','Service momentanément inaccessible.'));});
doc$('refreshAdmin')?.addEventListener('click',()=>loadAdmin().catch(()=>docMsg('adminNotice','Service momentanément inaccessible.')));
const renewalWarning=document.createElement('p');renewalWarning.className='muted';renewalWarning.id='documentRenewalWarning';
renewalWarning.textContent='Actualisez vos quatre catégories de justificatifs tous les six mois à compter de leur dépôt, ou plus tôt si leur validité expire. Renouvellement : la nouvelle pièce est prise en compte dès son dépôt. Tant qu’elle reste en attente de validation par 13 URGENT, vos nouvelles propositions et attributions peuvent être suspendues.';
doc$('documentForm').before(renewalWarning);
doc$('documentForm').addEventListener('submit',uploadDocument);
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>doc$(b.dataset.close).close()));
function clearProfessionalViews(){
 if(doc$('adminPageNotice'))doc$('adminPageNotice').textContent='Connectez-vous avec votre compte administrateur pour accéder à la gestion.';
 for(const name of ['documentsDialog','adminDialog'])if(doc$(name)?.open)doc$(name).close();
 for(const name of ['myDocuments','adminDossiers'])doc$(name)?.replaceChildren();
 doc$('companyStatus').textContent='';doc$('documentForm').reset();doc$('documentFile').required=true;
 for(const name of ['documentNotice','adminNotice']){if(doc$(name)){doc$(name).textContent='';doc$(name).hidden=true;}}
}
sb?.auth.onAuthStateChange((event,session)=>{if(event==='TOKEN_REFRESHED'||event==='SIGNED_IN'&&session?.user?.id===professionalSessionId)return;setTimeout(()=>{
 const id=session?.user?.id||null;
 if(id!==professionalSessionId){
  professionalSessionId=id;professionalAccessGeneration++;professionalProfile=null;clearProfessionalViews();
 }
 refreshProfessionalAccess().catch(()=>{});
},0);});
refreshProfessionalAccess().catch(()=>{});
