'use strict';
(()=>{
 const knowledge=window.urgentSupportKnowledge;if(!knowledge)return;
 const isAdmin=document.body.dataset.adminPage==='true';
 if(!isAdmin&&!['/','/index.html'].includes(location.pathname))return;
 const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 let generation=0,busy=false,capabilities=null;
 const client=()=>typeof sb!=='undefined'?sb:null;
 async function invoke(body){
  if(!window.URGENT_SUPABASE_URL||!window.URGENT_SUPABASE_PUBLISHABLE_KEY)throw Error('unavailable');
  const headers={apikey:window.URGENT_SUPABASE_PUBLISHABLE_KEY,'Content-Type':'application/json'};
  if(body.action!=='status'){
   let timer;let session;try{session=await Promise.race([client()?.auth?.getSession(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('session_timeout')),8000);})]);}finally{clearTimeout(timer);}const token=session?.data?.session?.access_token;if(!token)throw Error('signin');headers.Authorization='Bearer '+token;
  }
  const response=await fetch(window.URGENT_SUPABASE_URL+'/functions/v1/support-assistant',{method:'POST',headers,body:JSON.stringify(body),credentials:'omit',signal:AbortSignal.timeout(body.action==='status'?6000:60000)});
  if(!response.ok&&body.action==='notify_business_validation'&&response.status===400){let data;try{data=await response.json();}catch{}if(data?.error==='invalid_action')return{notified:false,notification_status:'service_update_required'};throw Error('unavailable');}
  if(!response.ok&&body.action==='reply_ticket'&&response.status===400){let error;try{error=await response.json();}catch{}if(error?.error==='invalid_action'){const saved=await client().rpc('urgent_support_reply',{p_ticket:body.ticket_id,p_reply:body.reply,p_status:'in_progress'});if(saved.error)throw Error('unavailable');return{ticket_id:body.ticket_id,saved:true,notified:false,notification_status:'service_update_required'};}}
  if(!response.ok){if(response.status===401)throw Error('signin');if(response.status===429)throw Error('limit');if(response.status===413)throw Error('large_document');if(response.status===422)throw Error('document_unreadable');throw Error('unavailable');}
  const result=await response.json();return result;
 }
 async function status(){try{const data=await invoke({action:'status'});capabilities=data.enabled===true?data:null;}catch{capabilities=null;}return capabilities;}
 async function currentProfile(){
  const api=client();if(!api)throw Error('signin');const auth=await api.auth.getUser();if(auth.error||!auth.data?.user)throw Error('signin');
  const profile=await api.from('profiles').select('id,role,company_id').eq('id',auth.data.user.id).single();if(profile.error||!profile.data)throw Error('profile');return profile.data;
 }
 function readable(error){if(error.message==='session_timeout')return 'La vérification de votre connexion prend trop de temps. Fermez puis rouvrez votre espace de connexion avant de réessayer. Votre texte est conservé dans le formulaire.';if(error.message==='large_document')return 'Ce fichier dépasse la limite de préanalyse de 5 Mo. Le dépôt reste possible jusqu’à 10 Mo ; demandez son examen à l’administration.';if(error.message==='document_unreadable')return 'Le fichier ne peut pas être analysé. Vérifiez son format et sa lisibilité, ou demandez un examen à l’administration.';return error.message==='signin'?'Connectez-vous pour accéder à votre dossier privé.':error.message==='limit'?'La limite de demandes a été atteinte. Vous pouvez toujours utiliser les réponses rapides ou contacter l’administration.':'Le service de suivi n’est pas disponible pour le moment. Les réponses rapides restent accessibles. Contactez contact@13urgent.fr si vous êtes bloqué.';}
 function feedback(node,text){node.textContent=text;node.hidden=false;requestAnimationFrame(()=>{if(dialog.open||node.id==='supportReplyNotice')node.scrollIntoView({block:'nearest'});});}
 function adminDiagnostic(data){
  const d=data?.admin_diagnostic;if(!d||!Number.isInteger(d.http_status)||d.http_status<400||d.http_status>599)return '';
  const labels={quota_exhausted:'Crédit ou plafond de facturation API insuffisant : vérifier la facturation OpenAI.',authentication_failed:'Clé API refusée : vérifier OPENAI_API_KEY dans les secrets Supabase.',rate_limited:'Limite temporaire de requêtes API atteinte.',access_denied:'Droits de la clé ou du projet insuffisants.',model_unavailable:'Modèle IA configuré non accessible.',invalid_request:'Format de requête refusé par l’API : le service doit être vérifié.',provider_unavailable:'API IA momentanément indisponible.',provider_rejected:'Appel refusé par l’API IA.'};
  return Object.hasOwn(labels,d.category)?'\n\nDiagnostic administrateur : '+labels[d.category]+' (HTTP '+d.http_status+').':'';
 }
 const dialog=make('dialog');dialog.id='supportDialog';dialog.setAttribute('aria-labelledby','supportTitle');
 const header=make('div',undefined,'support-header');const title=make('h2','Assistance 13 URGENT');title.id='supportTitle';
 const close=make('button','Fermer','btn secondary');close.type='button';close.onclick=()=>dialog.close();header.append(title,close);
 const content=make('div',undefined,'support-content');content.append(make('p','Réponses immédiates aux questions courantes. Ne transmettez jamais de mot de passe, de code reçu par e-mail ou de lien de confirmation.','support-note'));
 const topics=make('div',undefined,'support-topics');const log=make('div');log.id='supportLog';log.setAttribute('role','log');log.setAttribute('aria-live','polite');log.setAttribute('aria-relevant','additions');
 function message(text,who='assistant'){
  const node=make('div',String(text).slice(0,7000),'support-message '+who);log.append(node);while(log.children.length>20)log.firstElementChild.remove();return node;
 }
 function welcome(){log.replaceChildren();message('Bonjour, je peux vous guider pour créer votre compte, déposer une demande, proposer un transport ou préparer vos justificatifs. Que souhaitez-vous faire ?');}
 function navigate(action){dialog.close();
  if(action==='account')document.getElementById('openAccount')?.click();
  else if(action==='documents'){const b=document.getElementById('openDocuments');if(b&&!b.hidden)b.click();else document.getElementById('openAccount')?.click();}
  else if(action==='diagnostic')openDiagnostic();
  else location.hash=action;
 }
 function answerTopic(key){const topic=knowledge.topics[key];if(!topic)return;const node=message(topic.answer);if(topic.action){const action=make('button',topic.action==='diagnostic'?'Vérifier mon dossier':'Ouvrir cette rubrique','btn secondary');action.type='button';action.onclick=()=>navigate(topic.action);node.append(make('br'),action);}}
 for(const[key,topic]of Object.entries(knowledge.topics)){const b=make('button',topic.label,'btn secondary');b.type='button';b.onclick=()=>answerTopic(key);topics.append(b);}
 content.append(topics,log);
 const form=make('form',undefined,'support-form');form.noValidate=true;const label=make('label','Votre question');const input=make('textarea');input.id='supportQuestion';input.rows=3;input.maxLength=1500;input.required=true;label.append(input);const send=make('button','Envoyer ma question','btn primary');send.type='submit';form.append(label,send);const questionStatus=make('p',undefined,'support-feedback');questionStatus.id='supportQuestionStatus';questionStatus.setAttribute('role','status');questionStatus.hidden=true;content.append(form,questionStatus,make('p','L’assistant vous répond ici. Pour prévenir l’équipe, utilisez « Transmettre mon problème ».','support-note'));
 const controls=make('div',undefined,'support-controls');
 function control(text,fn){const b=make('button',text,'btn secondary');b.type='button';b.onclick=fn;controls.append(b);return b;}
 const contact=make('a','Écrire à l’administration','btn secondary');contact.href='mailto:contact@13urgent.fr?subject=Assistance%2013%20URGENT';controls.append(contact);
 const diagnostic=control('Vérifier mon dossier',openDiagnostic);
 const ticket=control('Transmettre mon problème',()=>{ticketForm.hidden=!ticketForm.hidden;if(!ticketForm.hidden)ticketText.focus();});ticket.hidden=true;
 const historyButton=control('Mes échanges avec l’administration',()=>loadTickets(false));historyButton.hidden=true;
 content.append(controls);
 const ticketForm=make('form',undefined,'support-form');ticketForm.noValidate=true;ticketForm.hidden=true;const ticketLabel=make('label','Décrivez le problème à transmettre à l’administration (10 caractères minimum)');const ticketText=make('textarea');ticketText.id='supportTicketText';ticketText.maxLength=1500;ticketText.rows=4;ticketText.required=true;ticketText.minLength=10;ticketLabel.append(ticketText);const ticketSubmit=make('button','Enregistrer ma demande d’assistance','btn primary');ticketSubmit.type='submit';ticketForm.append(ticketLabel,ticketSubmit);const ticketStatus=make('p',undefined,'support-feedback');ticketStatus.id='supportTicketStatus';ticketStatus.setAttribute('role','status');ticketStatus.hidden=true;content.append(ticketForm,ticketStatus);
 const tickets=make('div',undefined,'support-tickets');tickets.id='supportTickets';tickets.hidden=true;content.append(tickets);
 dialog.append(header,content);document.body.append(dialog);
 const launcher=make('button','Besoin d’aide ?','support-launcher');launcher.id='supportLauncher';launcher.type='button';launcher.setAttribute('aria-haspopup','dialog');launcher.setAttribute('aria-controls','supportDialog');launcher.onclick=()=>open();document.body.append(launcher);
 for(const[id,topic]of [['accountDialog','connexion'],['documentsDialog','documents']]){const modal=document.getElementById(id);if(!modal)continue;const help=make('button','Besoin d’aide ?','btn secondary');help.type='button';help.classList.add('support-modal-help');help.onclick=()=>open(topic);(modal.querySelector('.modal')||modal).append(help);}
 async function open(key){if(!dialog.open)dialog.showModal();if(!log.childElementCount)welcome();if(key)answerTopic(key);const version=generation;const ready=await status();if(version!==generation)return;ticket.hidden=!ready?.tickets_available;historyButton.hidden=!ready?.tickets_available;}
 async function openDiagnostic(){
  if(!dialog.open)dialog.showModal();const version=generation;diagnostic.disabled=true;
  try{
   const profile=await currentProfile();if(version!==generation)return;
   const company=await client().from('companies').select('name,verification_status').eq('id',profile.company_id).single();if(version!==generation)return;if(company.error)throw Error('unavailable');
   const statusNames={pending:'en attente d’examen',approved:'approuvé',verified:'vérifié',rejected:'refusé'};
   message('Établissement : '+(company.data?.name||'non renseigné')+'\nÉtat du dossier : '+(statusNames[company.data?.verification_status]||'à vérifier auprès de l’administration')+'.\nCet état ne suffit pas à prouver l’ensemble des droits de publication ou de proposition.');
   if(profile.role==='carrier'){
    const result=await client().rpc('urgent_document_checklist',{p_company:profile.company_id});if(version!==generation)return;if(result.error)throw Error('unavailable');
    const analysis=window.urgentDocumentAssistant?.analyseChecklist(result.data||[]);if(analysis)message(analysis.message+'\n'+analysis.items.map(x=>x.label+' : '+x.message).join('\n'));
   }else message('Pour un donneur d’ordre, la validation de l’établissement par 13 URGENT reste nécessaire avant publication. Une inscription et une confirmation d’e-mail ne remplacent pas cette validation.');
  }catch(e){if(version===generation)message(readable(e));}finally{diagnostic.disabled=false;}
 }
 form.onsubmit=async event=>{
  event.preventDefault();if(busy)return;const question=input.value.trim();if(!question||question.length>1500){feedback(questionStatus,'Saisissez votre question en 1 à 1 500 caractères.');return;}
  // Ne pas transmettre de jeton ni de mot de passe saisi par erreur.
  if(/(?:bearer\s+\S+|eyJ[A-Za-z0-9_-]{15,}\.|(?:mot de passe|password)\s*[:=]\s*\S+)/i.test(question)){feedback(questionStatus,'Retirez les mots de passe, jetons et codes privés avant d’envoyer votre question.');return;}
  message(question,'user');ticketText.value=question;const key=knowledge.match(question);if(key){answerTopic(key);input.value='';feedback(questionStatus,knowledge.topics[key].answer);return;}
  const version=generation;busy=true;send.disabled=true;send.textContent='Envoi en cours…';feedback(questionStatus,'Envoi de votre question en cours…');
  try{
   const ready=capabilities||await status();if(version!==generation)return;
   if(!ready){const text='Je n’ai pas de réponse fiable à cette question dans les réponses rapides. Vous pouvez écrire à contact@13urgent.fr pour qu’une personne vous accompagne.';message(text);feedback(questionStatus,text);return;}
   const data=await invoke({action:'ask',question});if(version!==generation)return;
   if(typeof data.answer!=='string'||!data.answer.trim())throw Error('unavailable');const answer=data.answer+adminDiagnostic(data);message(answer);input.value='';feedback(questionStatus,answer);
   if(data.escalate)message('Pour un examen de votre situation, utilisez « Transmettre mon problème ». Une demande n’est enregistrée qu’après votre confirmation.');
  }catch(e){if(version===generation){message(readable(e));feedback(questionStatus,readable(e));}}finally{busy=false;send.disabled=false;send.textContent='Envoyer ma question';}
 };
 ticketForm.onsubmit=async event=>{
  event.preventDefault();if(ticketSubmit.disabled)return;const text=ticketText.value.trim();if(text.length<10||text.length>1500){feedback(ticketStatus,'Décrivez votre problème en au moins 10 caractères (1 500 maximum). Aucun envoi n’a été effectué.');return;}if(/(?:bearer\s+\S+|eyJ[A-Za-z0-9_-]{15,}\.|(?:mot de passe|password)\s*[:=]\s*\S+)/i.test(text)){feedback(ticketStatus,'Retirez les mots de passe et jetons de votre demande.');return;}const version=generation;ticketSubmit.disabled=true;ticketSubmit.textContent='Envoi en cours…';feedback(ticketStatus,'Enregistrement de votre demande en cours…');
  try{const data=await invoke({action:'ticket',subject:'Assistance depuis le site',message:text});if(version!==generation)return;if(typeof data.ticket_id!=='string')throw Error('unavailable');ticketForm.hidden=true;ticketText.value='';const confirmation='Votre demande est enregistrée sous la référence '+data.ticket_id+'. '+(data.notified?'Une alerte a été transmise à l’administration.':'L’envoi de l’alerte n’est pas confirmé ; votre demande reste consultable dans le suivi.');message(confirmation);feedback(ticketStatus,confirmation);}
  catch(e){if(version===generation){message(readable(e));feedback(ticketStatus,readable(e));}}finally{ticketSubmit.disabled=false;ticketSubmit.textContent='Enregistrer ma demande d’assistance';}
 };
 const ticketLoads={admin:0,client:0};
 async function loadTickets(admin=false){
  const loadKey=admin?'admin':'client';const load=++ticketLoads[loadKey];const version=generation;const stale=()=>version!==generation||load!==ticketLoads[loadKey];const host=admin?adminList:tickets;host.hidden=false;host.replaceChildren(make('p','Chargement des échanges…'));
  try{const profile=await currentProfile();if(stale())return;if(admin&&profile.role!=='admin')throw Error('signin');
   const rows=[];const size=200;
   for(let offset=0;;offset+=size){
    let query=client().from('urgent_support_tickets').select('id,created_by,company_id,subject,message,status,admin_reply,created_at,updated_at');if(!admin)query=query.eq('created_by',profile.id);
    query=query.order('created_at',{ascending:false}).order('id',{ascending:true});const paginated=typeof query.range==='function';
    const page=await(paginated?query.range(offset,offset+size-1):query.limit(size));if(stale())return;if(page.error)throw Error('unavailable');rows.push(...page.data||[]);
    if(!paginated||(page.data||[]).length<size)break;
   }
   const result={data:[...new Map(rows.map(row=>[row.id,row])).values()]};host.replaceChildren();
   if(!result.data?.length)host.append(make('p','Aucune demande d’assistance enregistrée.'));
   const ticketFolders=admin?window.urgentDossiers?.folders(host,[['review','Assistance à traiter'],['validated','Assistance traitée — classée']]):null;
   for(const row of result.data||[]){const card=make('article',undefined,'support-ticket');card.append(make('strong',row.subject),make('p','Référence : '+row.id+' · '+({open:'À traiter',in_progress:'En cours',resolved:'Traitée'}[row.status]||'À vérifier')),make('p',row.message));if(row.admin_reply)card.append(make('p','Réponse de l’administration :\n'+row.admin_reply));
    if(admin){const reply=make('form',undefined,'support-form');const l=make('label','Réponse au client');const field=make('textarea');field.required=true;field.maxLength=2500;field.value=row.admin_reply||'';l.append(field);const b=make('button','Envoyer la réponse au client et clôturer','btn primary');b.type='submit';reply.append(l,b);reply.onsubmit=async e=>{e.preventDefault();const v=generation;b.disabled=true;try{const data=await invoke({action:'reply_ticket',ticket_id:row.id,reply:field.value.trim(),status:'resolved'});if(v!==generation)return;if(data.saved!==true)throw Error('unavailable');await loadTickets(true);feedback(adminReplyNotice,data.notified?'Réponse enregistrée. Le service e-mail a accepté la notification'+(data.recipient_email?' à '+data.recipient_email:' au client')+(data.status==='in_progress'?' ; le dossier reste en cours, la clôture n’est pas confirmée.':'.'):data.notification_status==='service_update_required'?'Réponse enregistrée dans le suivi. Le service serveur doit être mis à jour pour envoyer l’e-mail au client.':'Réponse enregistrée dans le suivi, mais l’envoi e-mail au client n’est pas confirmé. État : '+String(data.notification_status||'à vérifier')+'.');}catch(err){if(v===generation)card.append(make('p',readable(err)));}finally{b.disabled=false;}};card.append(reply);}
    (ticketFolders?.containers[row.status==='resolved'?'validated':'review']||host).append(card);
   }
   ticketFolders?.update();
  }catch(e){if(!stale())host.replaceChildren(make('p',readable(e)));}
 }
 let adminList,adminReplyNotice;
 if(isAdmin){const section=make('section',undefined,'support-admin');section.id='supportAdmin';section.append(make('h2','Demandes d’assistance'));const b=make('button','Actualiser les demandes d’assistance','btn secondary');b.type='button';b.onclick=()=>loadTickets(true);adminList=make('div');adminReplyNotice=make('p',undefined,'support-feedback');adminReplyNotice.id='supportReplyNotice';adminReplyNotice.setAttribute('role','status');adminReplyNotice.hidden=true;section.append(b,adminReplyNotice,adminList);document.querySelector('main')?.append(section);}
 window.urgentSupport=Object.freeze({open,async notifyBusinessValidation(companyId,notifyPending=false){try{return await invoke({action:'notify_business_validation',company_id:companyId,notify_pending:notifyPending});}catch{return{notified:false,notification_status:'notification_failed'};}},issue(code){if(code==='otp_registration'){launcher.textContent='Besoin d’aide pour vous inscrire ?';launcher.dataset.topic='connexion';launcher.onclick=()=>open('connexion');}},async reviewDocument(documentId){
  if(!dialog.open)dialog.showModal();const version=generation;
  try{const ready=capabilities||await status();if(version!==generation)return;if(!ready){message('La préanalyse du contenu n’est pas encore disponible. Les contrôles techniques et la validation par l’administration restent accessibles.');return;}
   message('Préanalyse en cours. Cet avis ne vaut pas approbation du document.');const data=await invoke({action:'review_document',document_id:documentId});if(version!==generation)return;
   const review=data.review;if(!review||typeof review.summary!=='string')throw Error('unavailable');message(review.summary+'\n'+(Array.isArray(review.issues)?review.issues.join('\n'):'')+'\n'+(Array.isArray(review.unknowns)?review.unknowns.join('\n'):'')+'\nValidation finale réservée à l’administration.'+adminDiagnostic(data));
  }catch(e){if(version===generation)message(readable(e));}
 }});
 window.addEventListener('urgent-support-issue',event=>window.urgentSupport.issue(event.detail?.code));
 let supportSessionUser=null;
 client()?.auth?.onAuthStateChange?.((event,session)=>{if(event==='INITIAL_SESSION'){supportSessionUser=session?.user?.id||null;return;}if(!['SIGNED_IN','SIGNED_OUT','USER_DELETED'].includes(event))return;const next=session?.user?.id||null;if(next===supportSessionUser)return;supportSessionUser=next;generation++;capabilities=null;input.value='';ticketText.value='';questionStatus.textContent='';questionStatus.hidden=true;ticketStatus.textContent='';ticketStatus.hidden=true;tickets.replaceChildren();tickets.hidden=true;ticketForm.hidden=true;ticket.hidden=true;historyButton.hidden=true;adminList?.replaceChildren();if(adminReplyNotice){adminReplyNotice.textContent='';adminReplyNotice.hidden=true;}launcher.textContent='Besoin d’aide ?';launcher.onclick=()=>open();welcome();});
 welcome();
})();
