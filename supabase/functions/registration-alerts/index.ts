// @ts-nocheck
// Compatible Deno Edge Functions ; aucun secret ni destinataire fourni par la requête.
const RECIPIENT = 'saschronoss@outlook.com';
const SITE = 'https://13urgent.fr/';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clean = (value, max=180) => String(value ?? '').replace(/[\r\n\x00-\x1f\x7f]/g,' ').slice(0,max);
export function registrationEmail(row) {
 const company=clean(row.company_name)||'Entreprise à compléter';
 const type=row.account_type==='carrier'?'Transporteur':'Donneur d’ordre';
 const fields=[['Entreprise déclarée',company],['Type de compte',type],['E-mail',clean(row.email)],['SIRET déclaré',clean(row.siret)||'Non renseigné'],['Confirmation e-mail',row.email_confirmed?'Confirmée':'Pas encore confirmée'],['Inscription enregistrée',clean(row.registered_at)],['Référence entreprise',clean(row.company_id)],['Référence compte',clean(row.user_id)]];
 const note='Nouvelle inscription à examiner. Les informations ci-dessus sont déclaratives : cette alerte ne valide ni le SIRET, ni les documents, ni les droits d’accès.';
 const action='Connectez-vous avec votre compte administrateur, cliquez sur Administration et recherchez cette entreprise. Aucune pièce justificative n’est jointe à cet e-mail.';
 return {subject:`[13 URGENT] Nouvelle inscription ${type.toLowerCase()} — ${company}`,text:`${note}\n\n${fields.map(([k,v])=>`${k} : ${v}`).join('\n')}\n\n${action}\n${SITE}`,html:`<!doctype html><html lang="fr"><meta charset="utf-8"><body style="font:16px Arial,sans-serif;color:#171923;max-width:640px;margin:auto;padding:24px"><h1 style="font-size:24px">13 URGENT · Nouvelle inscription</h1><p>${escape(note)}</p><table cellpadding="8" style="border-collapse:collapse">${fields.map(([k,v])=>`<tr><th align="left" valign="top">${escape(k)}</th><td>${escape(v)}</td></tr>`).join('')}</table><p>${escape(action)}</p><p><a href="${SITE}" style="background:#e91d32;color:white;display:inline-block;padding:14px;text-decoration:none">Ouvrir 13 URGENT</a></p></body></html>`};
}
function json(status,body){return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json','cache-control':'no-store'}});}
export async function registrationAlertsHandler(request, env, fetcher=fetch) {
 if(request.method!=='POST')return json(405,{error:'method_not_allowed'});
 const secret=env.REGISTRATION_ALERTS_SECRET;
 if(!secret||secret.length<32)return json(503,{error:'not_configured'});
 if(request.headers.get('authorization')!==`Bearer ${secret}`)return json(401,{error:'unauthorized'});
 const alertsEnabled=env.REGISTRATION_ALERTS_ENABLED==='true',monthlyEnabled=env.MONTHLY_REPORTS_ENABLED==='true';
 if(!alertsEnabled&&!monthlyEnabled)return json(200,{enabled:false});
 let base;
 try{base=new URL(env.SUPABASE_URL);if(base.protocol!=='https:'||base.pathname!=='/')throw Error();}catch{return json(503,{error:'not_configured'});}
 if(!env.SUPABASE_SERVICE_ROLE_KEY||!env.RESEND_API_KEY||!/^.+<[^<>\s@]+@[^<>\s@]+>$/.test(env.REGISTRATION_ALERTS_FROM||'')||/[\r\n]/.test(env.REGISTRATION_ALERTS_FROM))return json(503,{error:'not_configured'});
 const rpc=async(name,data)=>{
  const response=await fetcher(`${base.origin}/rest/v1/rpc/${name}`,{method:'POST',headers:{apikey:env.SUPABASE_SERVICE_ROLE_KEY,authorization:`Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,'content-type':'application/json'},body:JSON.stringify(data),signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw Error('database_error');return response.json();
 };
 const monthly=monthlyEnabled?await sendMonthlyReport(env,fetcher,rpc):null;
 let rows;
 try{rows=alertsEnabled?await rpc('urgent_claim_registration_alerts',{}):[];if(!Array.isArray(rows))throw Error();}catch{return json(502,{error:'database_error'});}
 let sent=0,retry=0;
 for(const row of rows){
  if(!uuid.test(row.alert_id)||!uuid.test(row.lease_token)||!uuid.test(row.user_id))return json(502,{error:'invalid_job'});
  let success=false,providerId=null,errorCode='send_error';
  try{
   const mail=registrationEmail(row);
   const response=await fetcher('https://api.resend.com/emails',{method:'POST',headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','Idempotency-Key':`registration-alert/${row.alert_id}`},body:JSON.stringify({from:env.REGISTRATION_ALERTS_FROM,to:[RECIPIENT],...mail}),signal:AbortSignal.timeout(10000)});
   if(response.ok){const result=await response.json();if(typeof result.id==='string'&&result.id){success=true;providerId=result.id;}else errorCode='provider_invalid_response';}
   else errorCode=`provider_http_${response.status}`;
  }catch{errorCode='provider_network_error';}
  try{const done=await rpc('urgent_finish_registration_alert',{p_alert_id:row.alert_id,p_lease_token:row.lease_token,p_success:success,p_provider_id:providerId,p_error_code:success?null:errorCode});if(done!==true)throw Error();}catch{return json(502,{error:'acknowledgement_failed'});}
  if(success)sent++;else retry++;
 }
 return json(monthly?.error?502:200,{enabled:true,sent,retry,...(monthly?{monthly}:{})});
}

// Récapitulatif mensuel interne : aucune émission de facture ou modification de frais.
function reportMoney(cents){return new Intl.NumberFormat('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(cents/100)+' €';}
function reportDate(value){return new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',dateStyle:'short',timeStyle:'short'}).format(new Date(value));}
function reportBase64(value){const bytes=new TextEncoder().encode(value);let result='';for(let i=0;i<bytes.length;i+=32768)result+=String.fromCharCode(...bytes.subarray(i,i+32768));return btoa(result);}
function reportCell(value,numeric=false){let text=String(value??'');if(!numeric&&(/^[\s]*[=+@-]/.test(text)||/^[\t\r\n]/.test(text)))text="'"+text;return '"'+text.replaceAll('"','""')+'"';}
export function monthlyReportEmail(job){
 const data=job.snapshot;if(!data||data.month!==job.month||!/^\d{4}-\d{2}-01$/.test(data.month)||!Array.isArray(data.entries)||!Array.isArray(data.subscriptions))throw Error('invalid_report');
 const month=data.month.slice(0,7),groups=new Map();let net=0,unbilled=0;
 const headers=['entreprise','siret','entreprise_id','ecriture_id','course_id','offre_id','depart','destination','date_Paris','nature','transport_HT_eur','frais_HT_eur','reference_facture','ecriture_origine','facture_origine','motif'];
 const csv=['\uFEFF'+headers.map(x=>reportCell(x)).join(';')];
 for(const row of data.entries){
  if(!Number.isSafeInteger(row.amount_ht_cents)||!['fee','credit'].includes(row.kind))throw Error('invalid_report');
  let group=groups.get(row.company_id);if(!group){group={name:String(row.company_name??''),siret:String(row.siret??''),rows:[],net:0,unbilled:0};groups.set(row.company_id,group);}
  group.rows.push(row);group.net+=row.amount_ht_cents;net+=row.amount_ht_cents;
  if(!row.invoice_reference){group.unbilled+=row.amount_ht_cents;unbilled+=row.amount_ht_cents;}
  const values=[row.company_name,row.siret,row.company_id,row.entry_id,row.shipment_id,row.offer_id,row.origin,row.destination,reportDate(row.occurred_at),row.kind==='fee'?'Frais de mise en relation':'Régularisation',row.transport_ht,String(row.amount_ht_cents/100).replace('.',','),row.invoice_reference,row.parent_id,row.original_invoice_reference,row.reason];
  // Les prix du transport restent des données de référence, non des revenus CHRONOSS à additionner.
  csv.push(values.map((value,i)=>reportCell(value,i===11)).join(';'));
 }
 if(!Number.isSafeInteger(net)||!Number.isSafeInteger(unbilled))throw Error('invalid_report');
 const generated=reportDate(data.generated_at);
 const warning=(data.test===true?'TEST D’ENVOI — ':'')+'DOCUMENT PRÉPARATOIRE — NE CONSTITUE PAS UNE FACTURE. Montants HT ; TVA à déterminer dans votre outil de facturation. Aucun numéro de facture attribué, aucun paiement déclenché.';
 const summary=[...groups.values()].map(g=>`<tr><td>${escape(g.name)}</td><td>${reportMoney(g.net)}</td><td>${reportMoney(g.unbilled)}</td></tr>`).join('');
 const details=[...groups.values()].map(g=>`<section class="company"><h2>${escape(g.name)}</h2><p>SIRET déclaré : ${escape(g.siret||'à compléter')} · Référence entreprise : ${escape(g.rows[0].company_id)}</p><table><thead><tr><th>Course / écriture</th><th>Date Paris</th><th>Nature</th><th>Frais HT</th><th>Facturation</th></tr></thead><tbody>${g.rows.map(r=>`<tr><td>${escape(r.origin)} → ${escape(r.destination)}<br>Course ${escape(r.shipment_id)}<br>Écriture ${escape(r.entry_id)}</td><td>${escape(reportDate(r.occurred_at))}</td><td>${r.kind==='fee'?'Frais de mise en relation':'Régularisation'}<br>${escape(r.reason)}${r.parent_id?'<br>Origine : '+escape(r.parent_id):''}${r.original_invoice_reference?'<br>Facture d’origine : '+escape(r.original_invoice_reference):''}</td><td>${reportMoney(r.amount_ht_cents)}</td><td>${r.invoice_reference?'Déjà rapproché : '+escape(r.invoice_reference):'À rapprocher avant émission'}</td></tr>`).join('')}</tbody></table><p><strong>Net du mois : ${reportMoney(g.net)} HT. Non rapproché à la génération : ${reportMoney(g.unbilled)} HT.</strong></p><p>Un solde négatif appelle l’examen d’un avoir. Vérifier les factures et régularisations déjà émises avant toute émission.</p></section>`).join('');
 const subscriptions=data.subscriptions.map(p=>{if(!Number.isSafeInteger(p.received_cents))throw Error('invalid_report');return `<tr><td>${escape(p.company_name)}</td><td>${escape(p.plan)}</td><td>${escape(reportDate(p.starts_at))} → ${escape(reportDate(p.ends_at))}</td><td>${reportMoney(p.received_cents)} TTC</td><td>${escape(p.invoice_reference)}${p.revoked_at?' · révoquée le '+escape(reportDate(p.revoked_at)):''}</td></tr>`;}).join('');
 const top=`<h1>CHRONOSS / 13 URGENT — Préparation de facturation</h1><p>Mois : ${escape(month)} · Généré le ${escape(generated)} (Paris).</p><p class="warning">${warning}</p><p>Relevé figé à sa génération. Les écritures marquées comme déjà facturées sont présentées pour contrôle et ne sont pas à facturer une seconde fois. Les corrections postérieures seront à rapprocher avec le relevé suivant.</p><h2>Synthèse par entreprise</h2><table><thead><tr><th>Entreprise</th><th>Net des écritures HT</th><th>Non rapproché HT</th></tr></thead><tbody>${summary||'<tr><td colspan="3">Aucune écriture de frais sur ce mois.</td></tr>'}</tbody></table><p>Net total : <strong>${reportMoney(net)} HT</strong> · Non rapproché : <strong>${reportMoney(unbilled)} HT</strong>.</p>`;
 const sub=`<h2>Abonnements enregistrés ou révoqués pendant le mois — suivi uniquement</h2><p>Les périodes ci-dessous comportent déjà une référence de facture et un règlement enregistré. Ne pas les ajouter à nouveau aux frais à facturer. Les montants sont TTC et ne sont pas additionnés aux bases HT ci-dessus.</p><table><thead><tr><th>Entreprise</th><th>Forfait</th><th>Période</th><th>Règlement enregistré</th><th>Facture</th></tr></thead><tbody>${subscriptions||'<tr><td colspan="5">Aucune période enregistrée sur ce mois.</td></tr>'}</tbody></table>`;
 const html=`<!doctype html><html lang="fr"><meta charset="utf-8"><title>Préparation CHRONOSS ${month}</title><style>body{font:14px Arial,sans-serif;line-height:1.5;color:#17212b;max-width:1100px;margin:auto;padding:24px}h1{font-size:24px}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}.warning{background:#fff0d8;padding:14px;font-weight:bold}.company{margin-top:32px}@media print{.company{break-before:page}tr{break-inside:avoid}body{max-width:none;padding:0;font-size:10pt}}</style>${top}${details}${sub}<p>Document interne réservé à CHRONOSS. Aucun envoi aux entreprises clientes.</p></html>`;
 const csvText=csv.join('\r\n')+'\r\n';if(new TextEncoder().encode(html+csvText).length>6000000)throw Error('report_too_large');
 return {subject:`[13 URGENT] ${data.test===true?'TEST — ':''}Préparation de facturation — ${month}`,text:`Préparation de facturation ${month}. ${groups.size} entreprise(s). Net : ${reportMoney(net)} HT ; non rapproché : ${reportMoney(unbilled)} HT. ${warning} Les abonnements déjà référencés sont séparés pour éviter une double facturation. Voir le relevé HTML imprimable et le CSV joints.`,html:`${top}<p>Le détail par entreprise et le suivi des abonnements sont dans le document HTML joint, imprimable en PDF depuis votre navigateur. Le CSV reprend les écritures de frais et régularisations.</p>`,attachments:[{filename:`13URGENT-preparation-${month}.html`,content:reportBase64(html)},{filename:`13URGENT-ecritures-${month}.csv`,content:reportBase64(csvText)}]};
}
async function sendMonthlyReport(env,fetcher,rpc){
 let jobs;try{jobs=await rpc('urgent_claim_monthly_report',{});if(!Array.isArray(jobs))throw Error();}catch{return {error:'monthly_database_error'};}
 if(!jobs.length)return {sent:0,retry:0};const job=jobs[0];if(!uuid.test(job.report_id)||!uuid.test(job.lease_token))return {error:'invalid_monthly_job'};
 let success=false,provider=null,code='send_error',permanent=false;
 try{
  const mail=monthlyReportEmail(job);const response=await fetcher('https://api.resend.com/emails',{method:'POST',headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','Idempotency-Key':`monthly-report/${job.report_id}`},body:JSON.stringify({from:env.REGISTRATION_ALERTS_FROM,to:[RECIPIENT],...mail}),signal:AbortSignal.timeout(10000)});
  if(response.ok){const result=await response.json();if(typeof result.id==='string'&&result.id){success=true;provider=result.id;}else code='provider_invalid_response';}else code=`provider_http_${response.status}`;
 }catch(error){if(['report_too_large','invalid_report'].includes(error.message)){code=error.message;permanent=true;}else code='provider_network_error';}
 try{const done=await rpc('urgent_finish_monthly_report',{p_report_id:job.report_id,p_lease_token:job.lease_token,p_success:success,p_provider_id:provider,p_error_code:success?null:code,p_permanent:permanent});if(done!==true)throw Error();}catch{return {error:'monthly_acknowledgement_failed'};}
 return {sent:success?1:0,retry:success||permanent?0:1,...(permanent?{error:code}:{})};
}

if(typeof Deno!=='undefined')Deno.serve(request=>registrationAlertsHandler(request,Deno.env.toObject()));
