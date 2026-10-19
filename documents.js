"use strict";
// Les actions utilisent exclusivement la session utilisateur et les politiques Supabase.
const DOC_BUCKET='carrier-documents';
const documentLabels={registration:'Immatriculation / Kbis',transport_licence:'Licence de transport',insurance_rc:'Assurance responsabilité civile',insurance_goods:'Assurance marchandises transportées',other:'Autre document'};
const documentLabel=kind=>documentLabels[kind]||kind;
const doc$=id=>document.getElementById(id);
function docMsg(id,message){const e=doc$(id);e.hidden=false;e.textContent=message;}
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
    const c=await getOwnCompany();doc$('companyStatus').textContent=`${c.name} — Dossier : ${c.verification_status}`;
    const {data,error}=await sb.from('carrier_documents').select('id,document_type,original_filename,review_status,expires_on,created_at').eq('company_id',c.id).order('created_at',{ascending:false});
    if(error)throw error;
    if(generation!==professionalAccessGeneration)return;
    const host=doc$('myDocuments');host.replaceChildren();
    if(!data?.length)line(host,'p','Aucun justificatif envoyé.');
    for(const d of data){const item=line(host,'div','', 'doc-item');line(item,'strong',d.original_filename||d.document_type);line(item,'span',`${documentLabel(d.document_type)} · ${d.review_status}${d.expires_on?' · expire le '+d.expires_on:''}`);}
  }catch(e){docMsg('documentNotice','Erreur : '+e.message);}
}
async function uploadDocument(e){
  e.preventDefault();const btn=e.submitter;btn.disabled=true;doc$('documentNotice').hidden=true;
  try{
    if(professionalProfile?.role!=='carrier')throw Error('Connectez-vous avec un compte transporteur.');
    const company=await getOwnCompany();const file=doc$('documentFile').files[0];
    if(!file)throw Error('Choisissez un fichier.');
    if(file.size>10*1024*1024)throw Error('Le fichier dépasse 10 Mo.');
    const allowed={'application/pdf':'pdf','image/jpeg':'jpg','image/png':'png'};
    if(!allowed[file.type])throw Error('Formats autorisés : PDF, JPG et PNG.');
    const kind=doc$('documentType').value;
    if(kind!=='registration'&&!doc$('documentExpiry').value)throw Error('Renseignez la date de fin de validité figurant sur la licence ou l’assurance.');
    if(!['registration','transport_licence','insurance_rc','insurance_goods'].includes(kind))throw Error('Catégorie de document non prise en charge.');
    const path=`${company.id}/${crypto.randomUUID()}.${allowed[file.type]}`;
    const {error:uploadError}=await sb.storage.from(DOC_BUCKET).upload(path,file,{contentType:file.type,upsert:false});
    if(uploadError)throw uploadError;
    const row={company_id:company.id,document_type:kind,storage_path:path,original_filename:file.name,review_status:'pending'};
    if(doc$('documentExpiry').value)row.expires_on=doc$('documentExpiry').value;
    const {error}=await sb.from('carrier_documents').insert(row);
    if(error)throw Error('Fichier envoyé mais fiche non enregistrée : '+error.message+' (contactez 13 URGENT).');
    doc$('documentFile').value='';await showMyDocuments();docMsg('documentNotice',`Document envoyé dans la catégorie « ${documentLabel(kind)} ». Il reste en attente de vérification par 13 URGENT.`);
  }catch(err){docMsg('documentNotice','Envoi impossible : '+err.message);}finally{btn.disabled=false;}
}
async function showAdmin(){
  if(professionalProfile?.role!=='admin')return;
  doc$('adminDialog').showModal();await loadAdmin();
}
async function loadAdmin(){
  if(professionalProfile?.role!=='admin')return;
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
      if(d.review_status==='pending'){
        for(const [status,label] of [['approved','Accepter'],['rejected','Refuser']]){
          const b=line(buttons,'button',label,status==='approved'?'btn primary':'btn secondary');b.type='button';
          b.onclick=async()=>{
            if(!confirm(`${label} ce document ?`))return;
            b.disabled=true;
            const {data:{user}}=await sb.auth.getUser();
            const {error}=await sb.from('carrier_documents').update({review_status:status,reviewed_at:new Date().toISOString(),reviewed_by:user.id}).eq('id',d.id);
            if(error){docMsg('adminNotice','Validation impossible : '+error.message);b.disabled=false;return;}
            await loadAdmin();docMsg('adminNotice',`Document ${status==='approved'?'accepté':'refusé'}. L’entreprise n’est pas automatiquement validée.`);
          };
        }
      }
    }
  }
}
doc$('openDocuments').addEventListener('click',()=>showMyDocuments().catch(()=>docMsg('documentNotice','Service momentanément inaccessible.')));
doc$('openAdmin').addEventListener('click',()=>showAdmin().catch(()=>docMsg('adminNotice','Service momentanément inaccessible.')));
doc$('refreshAdmin').addEventListener('click',()=>loadAdmin().catch(()=>docMsg('adminNotice','Service momentanément inaccessible.')));
doc$('documentForm').addEventListener('submit',uploadDocument);
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>doc$(b.dataset.close).close()));
function clearProfessionalViews(){
 for(const name of ['documentsDialog','adminDialog'])if(doc$(name).open)doc$(name).close();
 for(const name of ['myDocuments','adminDossiers'])doc$(name).replaceChildren();
 doc$('companyStatus').textContent='';doc$('documentForm').reset();
}
sb?.auth.onAuthStateChange((_event,session)=>{setTimeout(()=>{
 const id=session?.user?.id||null;
 if(id!==professionalSessionId){
  professionalSessionId=id;professionalAccessGeneration++;professionalProfile=null;clearProfessionalViews();
 }
 refreshProfessionalAccess().catch(()=>{});
},0);});
refreshProfessionalAccess().catch(()=>{});
