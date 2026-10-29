const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const source=fs.readFileSync(__dirname+'/../supabase/functions/registration-alerts/index.ts','utf8');
 const{registrationAlertsHandler:handler,documentUploadEmail}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
 const uid=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0');
 const secret='x'.repeat(40),env={REGISTRATION_ALERTS_SECRET:secret,REGISTRATION_ALERTS_ENABLED:'true',SUPABASE_URL:'https://example.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'server-only',RESEND_API_KEY:'test-only',REGISTRATION_ALERTS_FROM:'13 URGENT <alertes@example.com>'};
 const req=()=>new Request('https://example.supabase.co/functions/v1/bright-service',{method:'POST',headers:{authorization:'Bearer '+secret},body:JSON.stringify({to:'intrus@example.com',document_id:uid(99)})});
 const row={alert_id:uid(1),lease_token:uid(2),document_id:uid(3),user_id:uid(4),company_id:uid(5),company_name:'<script>danger</script>\r\nBcc: intrus@example.com',account_type:'carrier',email:'carrier@example.com',document_type:'insurance_goods',original_filename:'<img src=x onerror=alert(1)>.pdf',uploaded_at:'2026-10-29T12:00:00Z'};
 const mail=documentUploadEmail(row);assert(!mail.subject.includes('\n'));assert(!mail.html.includes('<script>'));assert(!mail.html.includes('<img'));assert(mail.html.includes('&lt;img'));assert(mail.text.includes('Assurance marchandises'));assert(mail.text.includes('ne vaut pas validation'));assert(!mail.attachments);assert(documentUploadEmail({...row,account_type:'client'}).subject.includes('donneur d’ordre'));
 async function run({provider=200,ack=true,missing=false,network=false,invalid=false}={}){
  const calls=[];const fetcher=async(url,options)=>{
   const body=JSON.parse(options.body);calls.push({url,options,body});
   if(url.endsWith('urgent_claim_registration_alerts'))return Response.json([]);
   if(url.endsWith('urgent_claim_document_alerts'))return missing?Response.json({code:'PGRST202'},{status:404}):Response.json([{...row,...(invalid?{company_id:'invalid'}:{})}]);
   if(url.endsWith('urgent_finish_document_alert'))return Response.json(ack);
   assert.equal(url,'https://api.resend.com/emails');if(network)throw Error('Timeout');return Response.json(provider===200?{id:'provider-document'}:{message:'private error'},{status:provider});
  };return{response:await handler(req(),env,fetcher),calls};
 }
 let r=await run();assert.equal(r.response.status,200);assert.deepEqual((await r.response.json()).documents,{enabled:true,sent:1,retry:0});
 const sent=r.calls.find(c=>c.url==='https://api.resend.com/emails');assert.deepEqual(sent.body.to,['saschronoss@outlook.com']);assert.equal(sent.options.headers['Idempotency-Key'],'document-alert/'+row.alert_id);assert(!sent.body.attachments);
 let finish=r.calls.find(c=>c.url.endsWith('urgent_finish_document_alert'));assert.equal(finish.body.p_lease_token,row.lease_token);assert.equal(finish.body.p_success,true);
 r=await run({provider:429});finish=r.calls.find(c=>c.url.endsWith('urgent_finish_document_alert'));assert.equal(finish.body.p_success,false);assert.equal(finish.body.p_error_code,'provider_http_429');assert.equal((await r.response.json()).documents.retry,1);
 r=await run({network:true});assert.equal(r.calls.at(-1).body.p_error_code,'provider_network_error');
 r=await run({ack:false});assert.equal(r.response.status,502);assert.equal((await r.response.json()).documents.sent,0);
 r=await run({missing:true});assert.equal(r.response.status,200);assert.equal((await r.response.json()).documents.enabled,false);assert(!r.calls.some(c=>c.url==='https://api.resend.com/emails'));
 r=await run({invalid:true});assert.equal(r.response.status,502);assert(!r.calls.some(c=>c.url==='https://api.resend.com/emails'));
 console.log('PASS alertes documents HTTP : destinataire fixe, métadonnées échappées, aucun fichier privé joint, idempotence par pièce, erreur fournisseur/réseau, accusé DB et compatibilité avant migration.');
})().catch(e=>{console.error(e);process.exit(1)});
