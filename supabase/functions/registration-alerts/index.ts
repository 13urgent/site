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
 if(env.REGISTRATION_ALERTS_ENABLED!=='true')return json(200,{enabled:false});
 let base;
 try{base=new URL(env.SUPABASE_URL);if(base.protocol!=='https:'||base.pathname!=='/')throw Error();}catch{return json(503,{error:'not_configured'});}
 if(!env.SUPABASE_SERVICE_ROLE_KEY||!env.RESEND_API_KEY||!/^.+<[^<>\s@]+@[^<>\s@]+>$/.test(env.REGISTRATION_ALERTS_FROM||'')||/[\r\n]/.test(env.REGISTRATION_ALERTS_FROM))return json(503,{error:'not_configured'});
 const rpc=async(name,data)=>{
  const response=await fetcher(`${base.origin}/rest/v1/rpc/${name}`,{method:'POST',headers:{apikey:env.SUPABASE_SERVICE_ROLE_KEY,authorization:`Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,'content-type':'application/json'},body:JSON.stringify(data),signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw Error('database_error');return response.json();
 };
 let rows;
 try{rows=await rpc('urgent_claim_registration_alerts',{});if(!Array.isArray(rows))throw Error();}catch{return json(502,{error:'database_error'});}
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
 return json(200,{enabled:true,sent,retry});
}
if(typeof Deno!=='undefined')Deno.serve(request=>registrationAlertsHandler(request,Deno.env.toObject()));
