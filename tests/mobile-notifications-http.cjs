const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const source=fs.readFileSync(__dirname+'/../supabase/functions/registration-alerts/index.ts','utf8');const{registrationAlertsHandler:handler,missionNotificationEmail}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
 const uid=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0'),secret='x'.repeat(40);
 const env={REGISTRATION_ALERTS_SECRET:secret,REGISTRATION_ALERTS_ENABLED:'true',SUPABASE_URL:'https://example.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'server',RESEND_API_KEY:'test',REGISTRATION_ALERTS_FROM:'13 URGENT <alertes@example.com>'};
 const req=()=>new Request('https://example.supabase.co/functions/v1/bright-service',{method:'POST',headers:{authorization:'Bearer '+secret},body:JSON.stringify({to:'intrus@example.com',recipient_email:'intrus@example.com'})});
 const row={alert_id:uid(1),lease_token:uid(2),shipment_id:uid(3),recipient_email:'owner@example.com',recipient_confirmed:true,recipient_allowed:true,origin:'<script>Paris</script>\r\nBcc:intrus',destination:'Lyon',event_type:'delivery_reported',filename:'<img src=x>.pdf',recorded_at:'2026-10-29T12:00:00Z'};
 const mail=missionNotificationEmail(row);assert(!mail.subject.includes('\n'));assert(!mail.html.includes('<script>'));assert(!mail.html.includes('<img'));assert(mail.text.includes('confirmez'));assert(!mail.attachments);assert(!mail.html.includes('/storage/'));
 async function run({job=row,provider=200,ack=true,missing=false,network=false}={}){
  const calls=[];const mock=async(url,options)=>{const body=JSON.parse(options.body);calls.push({url,options,body});
   if(url.endsWith('urgent_claim_registration_alerts')||url.endsWith('urgent_claim_document_alerts'))return Response.json([]);
   if(url.endsWith('urgent_claim_mission_notifications'))return missing?Response.json({code:'PGRST202'},{status:404}):Response.json(Array.isArray(job)?job:[job]);
   if(url.endsWith('urgent_finish_mission_notification'))return Response.json(ack);
   assert.equal(url,'https://api.resend.com/emails');if(network)throw Error('network');return Response.json(provider===200?{id:'provider-mission'}:{error:'private'},{status:provider});
  };return{response:await handler(req(),env,mock),calls};
 }
 let r=await run();assert.equal(r.response.status,200);assert.deepEqual((await r.response.json()).missions,{enabled:true,sent:1,retry:0});const send=r.calls.find(c=>c.url==='https://api.resend.com/emails');assert.deepEqual(send.body.to,['owner@example.com']);assert.equal(send.options.headers['Idempotency-Key'],'mission-notice/'+row.alert_id);assert(!send.body.attachments);
 r=await run({provider:429});assert.equal(r.calls.find(c=>c.url.endsWith('urgent_finish_mission_notification')).body.p_error_code,'provider_http_429');assert.equal((await r.response.json()).missions.retry,1);
 r=await run({network:true});assert.equal(r.calls.find(c=>c.url.endsWith('urgent_finish_mission_notification')).body.p_error_code,'provider_network_error');
 for(const field of['recipient_confirmed','recipient_allowed']){r=await run({job:{...row,[field]:false}});assert(!r.calls.some(c=>c.url==='https://api.resend.com/emails'));assert.equal((await r.response.json()).missions.retry,1);}
 r=await run({job:{...row,recipient_email:'bad\r\nBcc: x@example.com'}});assert(!r.calls.some(c=>c.url==='https://api.resend.com/emails'));
 r=await run({job:[row,{...row,alert_id:uid(4),lease_token:uid(5),recipient_confirmed:false}]});assert.deepEqual((await r.response.json()).missions,{enabled:true,sent:1,retry:1});
 r=await run({missing:true});assert.equal(r.response.status,200);assert.equal((await r.response.json()).missions.enabled,false);
 r=await run({ack:false});assert.equal(r.response.status,502);assert.equal((await r.response.json()).missions.sent,0);
 r=await run({job:{...row,event_type:'untrusted'}});assert.equal(r.response.status,502);assert(!r.calls.some(c=>c.url==='https://api.resend.com/emails'));
 console.log('PASS notifications missions : vrai destinataire confirmé, rattachement vérifié, pas de pièce jointe ni lien public, livraison déclarative, échappement, idempotence, lots mixtes, erreur fournisseur et accusé DB.');
})().catch(e=>{console.error(e);process.exit(1)});
