const fs=require('fs');const assert=require('node:assert/strict');
(async()=>{
 const source=fs.readFileSync(__dirname+'/../supabase/functions/registration-alerts/index.ts','utf8');
 const {registrationAlertsHandler:handler,registrationEmail}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
 const secret='x'.repeat(40),env={REGISTRATION_ALERTS_SECRET:secret,REGISTRATION_ALERTS_ENABLED:'true',SUPABASE_URL:'https://example.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'server-only',RESEND_API_KEY:'test-only',REGISTRATION_ALERTS_FROM:'13 URGENT <alertes@example.com>'};
 const row={alert_id:'00000000-0000-0000-0000-000000000001',lease_token:'00000000-0000-0000-0000-000000000002',user_id:'00000000-0000-0000-0000-000000000003',company_id:'00000000-0000-0000-0000-000000000004',company_name:'<script>alert(1)</script>\r\nBcc: intrus@example.com',account_type:'carrier',email:'carrier@example.com',siret:'12345678901234',email_confirmed:false,registered_at:'2026-10-21T12:00:00Z'};
 const req=(auth=secret)=>new Request('https://example.supabase.co/functions/v1/registration-alerts',{method:'POST',headers:{authorization:'Bearer '+auth},body:JSON.stringify({to:'intrus@example.com'})});
 let network=0;const never=async()=>{network++;throw Error('No network expected');};
 assert.equal((await handler(req('invalid'),env,never)).status,401);
 assert.equal((await handler(req(),{...env,REGISTRATION_ALERTS_ENABLED:'false'},never)).status,200);
 assert.equal((await handler(req(),{...env,RESEND_API_KEY:''},never)).status,503);assert.equal(network,0);
 const email=registrationEmail(row);assert(!email.subject.includes('\n'));assert(!email.html.includes('<script>'));assert(email.html.includes('&lt;script&gt;'));assert(email.text.includes('Pas encore confirmée'));assert(email.text.includes('déclaratives'));
 const run=async({provider=200,ack=true,throwSend=false}={})=>{
  const calls=[];const mock=async(url,options)=>{calls.push({url,options,body:JSON.parse(options.body)});
   if(url.endsWith('urgent_claim_registration_alerts'))return Response.json([row]);
   if(url.endsWith('urgent_finish_registration_alert'))return Response.json(ack);
   if(throwSend)throw Error('Timeout');return Response.json(provider===200?{id:'mail-test'}:{message:'private provider error'}, {status:provider});
  };const response=await handler(req(),env,mock);return {response,calls};
 };
 const good=await run();assert.equal(good.response.status,200);assert.deepEqual(await good.response.json(),{enabled:true,sent:1,retry:0});
 const sent=good.calls[1];assert.deepEqual(sent.body.to,['saschronoss@outlook.com']);assert.equal(sent.options.headers['Idempotency-Key'],'registration-alert/'+row.alert_id);assert.equal(good.calls[2].body.p_lease_token,row.lease_token);assert.equal(good.calls[2].body.p_success,true);
 const retry=await run({provider:429});assert.equal(retry.calls[2].body.p_success,false);assert.equal(retry.calls[2].body.p_error_code,'provider_http_429');assert.equal((await retry.response.json()).retry,1);
 const timeout=await run({throwSend:true});assert.equal(timeout.calls[2].body.p_error_code,'provider_network_error');
 assert.equal((await run({ack:false})).response.status,502);
 console.log('PASS alertes HTTP : authentification, arrêt, destinataire fixe, échappement, idempotence, échec fournisseur et accusé DB');
})().catch(e=>{console.error(e);process.exit(1)});
