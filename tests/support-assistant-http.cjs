const fs=require('fs');const assert=require('node:assert/strict');
(async()=>{
 const source=fs.readFileSync(__dirname+'/../supabase/functions/support-assistant/index.ts','utf8');
 const{supportAssistantHandler:handler}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
 const uid=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0');
 const env={SUPABASE_URL:'https://project.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'private-service-key',SUPABASE_ANON_KEY:'public-key'};
 const request=(body,token='user-token',origin='https://13urgent.fr')=>new Request('https://project.supabase.co/functions/v1/support-assistant',{method:'POST',headers:{origin,authorization:'Bearer '+token,'content-type':'application/json'},body:JSON.stringify(body)});
 function mock({foreign=false,reserved=true,ai=null,aiStatus=200,aiError=null,provider=200,large=false,role='carrier'}={}){
  const calls=[];const fetcher=async(url,options={})=>{
   let body;try{body=JSON.parse(options.body);}catch{}
   calls.push({url,options,body});
   if(url.endsWith('/auth/v1/user'))return Response.json(options.headers.authorization==='Bearer user-token'?{id:uid(3)}:{error:'bad_jwt'},{status:options.headers.authorization==='Bearer user-token'?200:401});
   if(url.includes('/rest/v1/profiles?'))return Response.json([{id:uid(3),role,company_id:uid(3)}]);
   if(url.includes('/rest/v1/companies?'))return Response.json([{name:'Entreprise de référence'}]);
   if(url.includes('/rest/v1/urgent_business_access?'))return Response.json([{siret:'91871039300052',registry_checked:true}]);
   if(url.endsWith('urgent_support_ready'))return Response.json(true);
   if(url.endsWith('urgent_support_reserve'))return Response.json(reserved);
   if(url.endsWith('urgent_support_create_ticket'))return Response.json(uid(90));
   if(url.includes('/rest/v1/carrier_documents?'))return Response.json([{id:uid(30),company_id:foreign?uid(4):uid(3),document_type:'insurance_rc',storage_path:(foreign?uid(4):uid(3))+'/file.png',review_status:'pending',expires_on:'2020-01-01'}]);
   if(url.endsWith('/rest/v1/urgent_document_prechecks'))return new Response(null,{status:204});
   if(url.includes('/storage/v1/object/'))return new Response(new Uint8Array([137,80,78,71,13,10,26,10,1]),{headers:{'content-type':'image/png',...(large?{'content-length':'6000000'}:{})}});
   if(url==='https://api.openai.com/v1/responses')return Response.json(aiStatus===200?{output_text:JSON.stringify(ai||{answer:'Une situation individuelle doit être examinée par l’administration.',escalate:true})}:aiError||{error:{code:'server_error'}},{status:aiStatus});
   if(url==='https://api.resend.com/emails')return Response.json(provider===200?{id:'mail-id'}:{error:'provider_rejected'},{status:provider});
   throw Error('Unexpected request '+url);
  };return{calls,fetcher};
 }
 let m=mock();let r=await handler(request({action:'status'}),env,m.fetcher);assert.equal(r.status,200);assert.deepEqual(await r.json(),{enabled:true,ai_available:false,document_ai_available:false,tickets_available:true});
 assert.equal((await handler(request({action:'ask',question:'Bonjour'},'forged-token'),env,m.fetcher)).status,401);
 assert.equal((await handler(request({action:'ask',question:'Bonjour'},env.SUPABASE_SERVICE_ROLE_KEY),env,m.fetcher)).status,401);
 assert.equal((await handler(request({action:'status'},'user-token','https://evil.example'),env,m.fetcher)).status,403);
 assert.equal((await handler(request({action:'status'}),{...env,SUPPORT_ASSISTANT_ENABLED:'false'},m.fetcher)).status,503);
 r=await handler(request({action:'ask',question:'Signups not allowed for otp'}),env,m.fetcher);assert.equal(r.status,200);assert.match((await r.json()).answer,/Créer mon compte/);assert(!m.calls.some(c=>c.url.includes('openai.com')));
 for(const question of ['Comment fonctionne le site ?','Comment ça marche ?','Pouvez-vous présenter l’utilisation de la plateforme ?','Présentation de la plateforme']){
  const general=mock();const result=await handler(request({action:'ask',question}),{...env,SUPPORT_AI_ENABLED:'true',OPENAI_API_KEY:'ai-private'},general.fetcher);const answer=await result.json();assert.equal(answer.source,'faq');assert.match(answer.answer,/met en relation/);assert(!general.calls.some(c=>c.url.includes('openai.com')));
 }
 r=await handler(request({action:'ask',question:'Mon contrat particulier nécessite un examen'}),env,m.fetcher);assert.equal((await r.json()).source,'human');
 m=mock();r=await handler(request({action:'ask',question:'Mon contexte privé, numéro 0612345678, +33 6 12 34 56 78, nom@example.com'}),{...env,SUPPORT_AI_ENABLED:'true',OPENAI_API_KEY:'ai-private'},m.fetcher);assert.equal(r.status,200);let aiCall=m.calls.find(c=>c.url.includes('openai.com'));assert.equal(aiCall.body.store,false);assert.equal(aiCall.body.max_output_tokens,500);assert(!aiCall.body.input.includes('nom@example.com'));assert(!aiCall.body.input.includes('0612345678'));assert(!aiCall.body.input.includes('+33 6'));
 await providerErrorChecks();
 m=mock({foreign:true});r=await handler(request({action:'review_document',document_id:uid(30)}),env,m.fetcher);assert.equal(r.status,404);assert(!m.calls.some(c=>c.url.includes('/storage/')));assert(!m.calls.some(c=>c.url.endsWith('urgent_support_reserve')));
 m=mock();r=await handler(request({action:'review_document',document_id:uid(30)}),env,m.fetcher);let data=await r.json();assert.equal(r.status,200);assert.equal(data.review.engine,'metadata');assert.equal(data.review.verdict,'needs_attention');assert(data.review.issues.some(x=>x.includes('expiré')));assert.equal(data.saved,true);assert(!m.calls.some(c=>c.url.includes('/storage/')));
 assert(!m.calls.some(c=>/carrier_documents/.test(c.url)&&['PATCH','POST'].includes(c.options.method)));
 m=mock({ai:{summary:'Pièce à rapprocher du dossier.',issues:[],unknowns:['Authenticité à contrôler.']}});r=await handler(request({action:'review_document',document_id:uid(30)}),{...env,SUPPORT_DOCUMENT_AI_ENABLED:'true',OPENAI_API_KEY:'ai-private'},m.fetcher);data=await r.json();assert.equal(data.review.engine,'openai');assert.notEqual(data.review.verdict,'approved');aiCall=m.calls.find(c=>c.url.includes('openai.com'));assert.equal(aiCall.body.store,false);assert.equal(aiCall.body.max_output_tokens,700);assert.equal(aiCall.body.input[0].content[1].type,'input_image');assert(aiCall.body.input[0].content[0].text.includes('Entreprise de référence'));assert(aiCall.body.input[0].content[0].text.includes('91871039300052'));assert(aiCall.body.input[0].content[0].text.includes('Date actuelle Europe/Paris'));assert(!m.calls.some(c=>c.url.includes('/files')));
 m=mock({large:true});r=await handler(request({action:'review_document',document_id:uid(30)}),{...env,SUPPORT_DOCUMENT_AI_ENABLED:'true',OPENAI_API_KEY:'ai-private'},m.fetcher);assert.equal(r.status,413);assert(!m.calls.some(c=>c.url.includes('openai.com')));
 m=mock({reserved:false});assert.equal((await handler(request({action:'ask',question:'Comment publier une demande ?'}),env,m.fetcher)).status,429);
 m=mock();r=await handler(request({action:'ticket',subject:'Inscription bloquée',message:'Je souhaite être accompagné pour mon inscription.',to:'evil@example.com',created_by:uid(99)}),{...env,RESEND_API_KEY:'mail-private',REGISTRATION_ALERTS_FROM:'13 URGENT <support@example.com>'},m.fetcher);data=await r.json();assert.deepEqual(data,{ticket_id:uid(90),notified:true});assert.equal(m.calls.find(c=>c.url.endsWith('urgent_support_create_ticket')).options.headers.authorization,'Bearer user-token');const email=m.calls.find(c=>c.url.includes('resend.com'));assert.deepEqual(email.body.to,['saschronoss@outlook.com']);assert.equal(email.options.headers['Idempotency-Key'],'support-ticket/'+uid(90));assert(email.body.text.includes('https://13urgent.fr/admin.html'));
 m=mock({provider:500});r=await handler(request({action:'ticket',subject:'Inscription bloquée',message:'Je souhaite être accompagné pour mon inscription.'}),{...env,RESEND_API_KEY:'mail-private',REGISTRATION_ALERTS_FROM:'13 URGENT <support@example.com>'},m.fetcher);assert.deepEqual(await r.json(),{ticket_id:uid(90),notified:false});
 assert.equal((await handler(request({action:'ask',question:'x'.repeat(1501)}),env,m.fetcher)).status,400);
 assert.equal((await handler(request({action:'ask',question:'x'.repeat(13000)}),env,m.fetcher)).status,413);
 await sqlChecks();
 console.log('PASS assistant : JWT réel vérifié, propriété documentaire, quotas, aucun droit métier modifié, limites fichiers, IA opt-in sans stockage, erreurs fournisseur diagnostiquées sans secret, FAQ générale sans IA, tickets privés et notification fixe/idempotente, SQL RLS et purge.');
 async function providerErrorChecks(){
  const originalWarn=console.warn;const logs=[];console.warn=(...args)=>logs.push(args.join(' '));
  try{
   const aiEnv={...env,SUPPORT_AI_ENABLED:'true',SUPPORT_DOCUMENT_AI_ENABLED:'true',OPENAI_API_KEY:'ai-private'};
   const cases=[
    [401,'invalid_api_key','authentication_failed'],
    [429,'insufficient_quota','quota_exhausted'],
    [429,'rate_limit_exceeded','rate_limited'],
    [403,'insufficient_permissions','access_denied'],
    [400,'unsupported_parameter','invalid_request'],
    [404,'model_not_found','model_unavailable'],
    [503,'server_error','provider_unavailable']
   ];
   for(const[http,code,category]of cases)for(const role of ['carrier','admin']){
    const provider=mock({role,aiStatus:http,aiError:{error:{code,message:'Never log ai-private nor the question: SITUATION-PRIVEE',type:'untrusted-type-ai-private'}}});
    const response=await handler(request({action:'ask',question:'SITUATION-PRIVEE à examiner personnellement.'}),aiEnv,provider.fetcher);assert.equal(response.status,200);const body=await response.json();assert.equal(body.source,'human');assert.equal(body.escalate,true);
    if(role==='admin')assert.deepEqual(body.admin_diagnostic,{category,http_status:http});else assert.equal(body.admin_diagnostic,undefined);
    const entry=JSON.parse(logs.at(-1));assert.deepEqual(entry,{event:'support_ai_provider_error',phase:'ask',http_status:http,category,code});assert(!JSON.stringify(body).includes('ai-private'));assert(!JSON.stringify(body).includes('SITUATION-PRIVEE'));
   }
   const malicious=mock({role:'admin',aiStatus:400,aiError:{error:{code:'ai-private',type:'SITUATION-PRIVEE',message:'ai-private'}}});
   await handler(request({action:'ask',question:'SITUATION-PRIVEE à examiner personnellement.'}),aiEnv,malicious.fetcher);assert.equal(JSON.parse(logs.at(-1)).code,'unknown');
   // Un document dont l'IA est refusée reste en contrôle de métadonnées, sans approbation.
   for(const role of ['carrier','admin']){
    const provider=mock({role,aiStatus:429,aiError:{error:{code:'insufficient_quota',message:'ai-private SITUATION-PRIVEE'}}});
    const response=await handler(request({action:'review_document',document_id:uid(30)}),aiEnv,provider.fetcher);const body=await response.json();assert.equal(response.status,200);assert.equal(body.review.engine,'metadata');assert.notEqual(body.review.verdict,'approved');assert.equal(body.saved,true);
    if(role==='admin')assert.deepEqual(body.admin_diagnostic,{category:'quota_exhausted',http_status:429});else assert.equal(body.admin_diagnostic,undefined);
    assert.equal(JSON.parse(logs.at(-1)).phase,'review_document');assert(!provider.calls.some(c=>c.url.includes('carrier_documents')&&c.options.method==='PATCH'));assert(!JSON.stringify(body).includes('ai-private'));assert(!JSON.stringify(body).includes('SITUATION-PRIVEE'));
   }
   assert(!JSON.stringify(logs).includes('ai-private'));assert(!JSON.stringify(logs).includes('SITUATION-PRIVEE'));assert(!JSON.stringify(logs).includes('untrusted-type'));
  }finally{console.warn=originalWarn;}
 }
})().catch(e=>{console.error(e);process.exit(1)});
async function sqlChecks(){
 const{createDatabase,uid}=require('./helpers/pilot-database.cjs');const{db,actor}=await createDatabase({includeBilling:false});
 try{
  await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610270001_support_assistant.sql','utf8'));
  await actor(3);const ticket=(await db.query("select public.urgent_support_create_ticket('Question dossier','Je souhaite une vérification de ma pièce.')as id")).rows[0].id;
  assert.equal((await db.query('select count(*) from public.urgent_support_tickets')).rows[0].count,1);
  await assert.rejects(db.query("insert into public.urgent_support_tickets(created_by,subject,message)values($1,'Intrusion','Tentative directe non autorisée')",[uid(4)]));
  await actor(4);assert.equal((await db.query('select count(*) from public.urgent_support_tickets')).rows[0].count,0);await assert.rejects(db.query("select public.urgent_support_reply($1,'Fausse validation','resolved')",[ticket]));
  await actor(1);assert.equal((await db.query('select count(*) from public.urgent_support_tickets')).rows[0].count,1);await db.query("select public.urgent_support_reply($1,'Merci de fournir une pièce lisible','in_progress')",[ticket]);
  await actor(3);assert.equal((await db.query('select admin_reply from public.urgent_support_tickets')).rows[0].admin_reply,'Merci de fournir une pièce lisible');
  for(let i=0;i<4;i++)await db.query("select public.urgent_support_create_ticket('Question dossier','Je souhaite une vérification de ma pièce.')");await assert.rejects(db.query("select public.urgent_support_create_ticket('Question dossier','Nouvelle demande au-delà du quota.')"));
  await assert.rejects(db.query("select public.urgent_support_reserve($1,'ai')",[uid(4)]));
  await db.exec('reset role;set role service_role');for(let i=0;i<10;i++)assert.equal((await db.query("select public.urgent_support_reserve($1,'ai')as ok",[uid(3)])).rows[0].ok,true);assert.equal((await db.query("select public.urgent_support_reserve($1,'ai')as ok",[uid(3)])).rows[0].ok,false);
  await db.exec('reset role');await db.exec("update public.urgent_support_tickets set updated_at=now()-interval '200 days'");await db.exec('set role service_role');await db.query('select public.urgent_support_purge()');await db.exec('reset role');assert.equal((await db.query('select count(*) from public.urgent_support_tickets')).rows[0].count,0);
 }finally{await db.close();}
}
