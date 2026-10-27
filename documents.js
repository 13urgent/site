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
let professionalProfile=null;
let professionalAccessGeneration=0;
let professionalSessionId=null;
async function refreshProfessionalAccess(){
  const generation=++professionalAccessGeneration;
  doc$('openDocuments').hidden=true;doc$('openAdmin').hidden=true;professionalProfile=null;
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
  doc$('openDocuments').hidden=data?.role!=='carrier';
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
  if(!professionalProfile||professionalProfile.role!=='carrier')return;
  doc$('documentsDialog').showModal();
  try{
    const c=await getOwnCompany();if(generation!==professionalAccessGeneration)return;doc$('companyStatus').textContent=`${c.name} — Dossier : ${c.verification_status}`;
    const {data,error}=await sb.from('carrier_documents').select('id,document_type,original_filename,review_status,expires_on,created_at').eq('company_id',c.id).order('created_at',{ascending:false});
    if(error)throw error;
    if(generation!==professionalAccessGeneration)return;
    const host=doc$('myDocuments');host.replaceChildren();
    if(!data?.length)line(host,'p','Aucun justificatif envoyé.');
    for(const d of data){const item=line(host,'div','', 'doc-item');line(item,'strong',d.original_filename||d.document_type);line(item,'span',`${documentLabel(d.document_type)} · ${d.review_status}${d.expires_on?' · expire le '+d.expires_on:''}`);if(window.urgentSupport){const help=line(item,'button','Demander une préanalyse','btn secondary');help.type='button';help.onclick=()=>window.urgentSupport.reviewDocument(d.id);}}
    if(typeof sb.rpc==='function'&&window.urgentDocumentAssistant){try{const checklist=await sb.rpc('urgent_document_checklist',{p_company:c.id});if(generation!==professionalAccessGeneration)return;if(!checklist.error&&Array.isArray(checklist.data)){const report=window.urgentDocumentAssistant.analyseChecklist(checklist.data);const panel=line(host,'div',report.message,'support-file-report');for(const item of report.items)line(panel,'p',item.label+' : '+item.message);}}catch{/* Le diagnostic ne bloque pas l’accès aux pièces. */}}
  }catch(e){if(generation===professionalAccessGeneration)docMsg('documentNotice','Erreur : '+e.message);}
}
async function uploadDocument(e){
  e.preventDefault();const btn=e.submitter;const generation=professionalAccessGeneration;btn.disabled=true;doc$('documentNotice').hidden=true;
  try{
    if(professionalProfile?.role!=='carrier')throw Error('Connectez-vous avec un compte transporteur.');
    const company=await getOwnCompany();if(generation!==professionalAccessGeneration)return;const file=doc$('documentFile').files[0];
    if(!file)throw Error('Choisissez un fichier.');
    if(file.size>10*1024*1024)throw Error('Le fichier dépasse 10 Mo.');
    const allowed={'application/pdf':'pdf','image/jpeg':'jpg','image/png':'png'};
    if(!allowed[file.type])throw Error('Formats autorisés : PDF, JPG et PNG.');
    const kind=doc$('documentType').value;const expiry=doc$('documentExpiry').value;
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
    doc$('documentFile').value='';await showMyDocuments();if(generation!==professionalAccessGeneration)return;docMsg('documentNotice',`Document envoyé dans la catégorie « ${documentLabel(kind)} ». Il reste en attente de vérification par 13 URGENT.`);
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
  const [companies,docs]=await Promise.all([
    sb.from('companies').select('id,name,company_type,verification_status').in('company_type',['carrier','both']).order('created_at',{ascending:false}),
    sb.from('carrier_documents').select('id,company_id,document_type,storage_path,original_filename,review_status,expires_on,created_at').order('created_at',{ascending:false})
  ]);
  if(generation!==professionalAccessGeneration)return;
  if(companies.error||docs.error){docMsg('adminNotice','Lecture impossible : '+(companies.error?.message||docs.error?.message));host.replaceChildren();return;}
  host.replaceChildren();if(!companies.data?.length){line(host,'p','Aucun transporteur enregistré.');return;}
  for(const c of companies.data){
    const card=line(host,'article','', 'dossier');line(card,'h3',c.name);line(card,'p',`Entreprise : ${c.verification_status} · ${c.id}`);
    const items=(docs.data||[]).filter(d=>d.company_id===c.id);
    if(!items.length)line(card,'p','Aucun document déposé.');
    for(const d of items){
      const row=line(card,'div','', 'doc-item');line(row,'strong',`${documentLabel(d.document_type)} — ${d.original_filename||'fichier'}`);
      line(row,'span',`Statut : ${d.review_status}${d.expires_on?' · Expiration : '+d.expires_on:''}`);
      const buttons=line(row,'div','', 'doc-actions');
      if(window.urgentSupport){const help=line(buttons,'button','Avis de l’assistant','btn secondary');help.type='button';help.onclick=()=>window.urgentSupport.reviewDocument(d.id);}
      const view=line(buttons,'button','Voir le fichier','btn secondary');view.type='button';view.onclick=async()=>{
        const {data,error}=await sb.storage.from(DOC_BUCKET).createSignedUrl(d.storage_path,60);
        if(error){docMsg('adminNotice','Fichier inaccessible : '+error.message);return;}
        window.open(data.signedUrl,'_blank','noopener,noreferrer');
      };
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
            }catch(e){if(actionGeneration===professionalAccessGeneration)docMsg('adminNotice','Validation impossible : '+e.message);}
            finally{b.disabled=false;}
          };
        }
      }
    }
  }
}
doc$('openDocuments').addEventListener('click',()=>showMyDocuments().catch(()=>docMsg('documentNotice','Service momentanément inaccessible.')));
if(adminPage)doc$('openAdmin').addEventListener('click',event=>{event.preventDefault();showAdmin().catch(()=>docMsg('adminNotice','Service momentanément inaccessible.'));});
doc$('refreshAdmin')?.addEventListener('click',()=>loadAdmin().catch(()=>docMsg('adminNotice','Service momentanément inaccessible.')));
const renewalWarning=document.createElement('p');renewalWarning.className='muted';renewalWarning.id='documentRenewalWarning';
renewalWarning.textContent='Renouvellement : la nouvelle pièce est prise en compte dès son dépôt. Tant qu’elle reste en attente de validation par 13 URGENT, vos nouvelles propositions et attributions peuvent être suspendues.';
doc$('documentForm').before(renewalWarning);
doc$('documentForm').addEventListener('submit',uploadDocument);
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>doc$(b.dataset.close).close()));
function clearProfessionalViews(){
 if(doc$('adminPageNotice'))doc$('adminPageNotice').textContent='Connectez-vous avec votre compte administrateur pour accéder à la gestion.';
 for(const name of ['documentsDialog','adminDialog'])if(doc$(name)?.open)doc$(name).close();
 for(const name of ['myDocuments','adminDossiers'])doc$(name)?.replaceChildren();
 doc$('companyStatus').textContent='';doc$('documentForm').reset();
 for(const name of ['documentNotice','adminNotice']){if(doc$(name)){doc$(name).textContent='';doc$(name).hidden=true;}}
}
sb?.auth.onAuthStateChange((_event,session)=>{setTimeout(()=>{
 const id=session?.user?.id||null;
 if(id!==professionalSessionId){
  professionalSessionId=id;professionalAccessGeneration++;professionalProfile=null;clearProfessionalViews();
 }
 refreshProfessionalAccess().catch(()=>{});
},0);});
refreshProfessionalAccess().catch(()=>{});
