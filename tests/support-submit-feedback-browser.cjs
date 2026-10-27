// Régression du clic silencieux : Supabase et tous les envois sont simulés.
const {chromium}=require('playwright');
const assert=require('assert/strict');

(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let ticketCalls=0,mode='failure',releaseTicket,signalTicket;
  const cors={'Access-Control-Allow-Origin':'https://site.example','Access-Control-Allow-Headers':'authorization,apikey,content-type','Access-Control-Allow-Methods':'POST, OPTIONS'};
  await page.route('https://api.example/**',async route=>{
   if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers:cors});
   const body=route.request().postDataJSON();
   if(body.action==='status')return route.fulfill({headers:cors,json:{enabled:true,tickets_available:true,ai_available:false}});
   if(body.action==='ask')return route.fulfill({headers:cors,json:{answer:'Votre situation nécessite un examen.',source:'human',escalate:true}});
   if(body.action==='ticket'){
    ticketCalls++;
    if(mode==='failure')return route.fulfill({status:503,headers:cors,json:{error:'ticket_not_created'}});
    const waiting=new Promise(resolve=>{releaseTicket=resolve;});signalTicket?.();await waiting;
    return route.fulfill({headers:cors,json:{ticket_id:'00000000-0000-0000-0000-000000000009',notified:true}});
   }
   return route.fulfill({status:400,headers:cors,json:{error:'unexpected_test_action'}});
  });
  await page.route('https://site.example/**',route=>{
   const file=new URL(route.request().url()).pathname.split('/').pop();
   if(['style.css','support.css','support-knowledge.js','support.js','document-assistant.js'].includes(file))return route.fulfill({path:__dirname+'/../'+file});
   return route.fulfill({contentType:'text/html; charset=utf-8',body:`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="support.css"></head><body><main><button id="openAccount">Compte</button><button id="openDocuments" hidden>Documents</button></main><footer></footer><script>
    window.URGENT_SUPABASE_URL='https://api.example';window.URGENT_SUPABASE_PUBLISHABLE_KEY='public-test';window.activeUser=null;window.authListeners=[];
    const sb={auth:{getUser:async()=>({data:{user:activeUser}}),getSession:async()=>({data:{session:activeUser?{access_token:'test-session'}:null}}),onAuthStateChange:cb=>authListeners.push(cb)}};
   </script><script src="support-knowledge.js"></script><script src="document-assistant.js"></script><script src="support.js"></script></body></html>`});
  });
  await page.goto('https://site.example/');
  await page.locator('#supportLauncher').click();
  await page.locator('#supportQuestion').fill('test');
  await page.getByRole('button',{name:'Envoyer ma question',exact:true}).click();
  await page.waitForFunction(()=>/connect/i.test(document.getElementById('supportQuestionStatus')?.textContent||''));
  await page.getByRole('button',{name:'Transmettre mon problème',exact:true}).click();
  assert.equal(await page.locator('#supportTicketText').inputValue(),'test');
  // Une valeur injectée par .value ne déclenche pas la contrainte native minlength.
  assert.equal(await page.locator('#supportTicketText').evaluate(e=>e.validity.tooShort),false);
  const submit=page.locator('#supportTicketText').locator('xpath=ancestor::form').locator('button[type=submit]');
  await submit.click();
  await page.waitForFunction(()=>/au moins 10 caract[eè]res/i.test(document.getElementById('supportTicketStatus')?.textContent||''));
  assert(await page.locator('#supportTicketStatus').isVisible());assert.equal(ticketCalls,0);
  assert.equal(await page.locator('#supportTicketText').inputValue(),'test');
  await page.locator('#supportTicketText').fill('            ');
  await submit.click();assert.match(await page.locator('#supportTicketStatus').innerText(),/au moins 10 caract[eè]res/i);assert.equal(ticketCalls,0);
  const text='Je souhaite une aide pour terminer mon inscription professionnelle.';
  await page.locator('#supportTicketText').fill(text);await submit.click();
  await page.waitForFunction(()=>/connect/i.test(document.getElementById('supportTicketStatus')?.textContent||''));
  assert(await page.locator('#supportTicketStatus').isVisible());assert.equal(ticketCalls,0);assert.equal(await page.locator('#supportTicketText').inputValue(),text);

  await page.evaluate(()=>{activeUser={id:'first'};authListeners.forEach(cb=>cb('SIGNED_IN',{user:activeUser}));});
  await page.locator('#supportDialog').getByRole('button',{name:'Fermer',exact:true}).click();
  await page.locator('#supportLauncher').click();
  await page.getByRole('button',{name:'Transmettre mon problème',exact:true}).click();
  await page.locator('#supportTicketText').fill(text);await submit.click();
  await page.waitForFunction(()=>/disponible|erreur|réessay/i.test(document.getElementById('supportTicketStatus')?.textContent||'')&&!document.getElementById('supportTicketText').form.querySelector('button[type=submit]').disabled);
  assert.equal(ticketCalls,1);assert.equal(await page.locator('#supportTicketText').inputValue(),text);assert.equal(await submit.isDisabled(),false);

  mode='pending';const arrived=new Promise(resolve=>{signalTicket=resolve;});
  await submit.click();await arrived;
  assert.equal(await submit.isDisabled(),true);assert.match(await submit.innerText(),/envoi en cours/i);
  // Supabase peut réémettre SIGNED_IN pour le même utilisateur pendant une requête.
  await page.evaluate(()=>authListeners.forEach(cb=>cb('SIGNED_IN',{user:{id:'first'}})));
  assert.equal(await page.locator('#supportTicketText').inputValue(),text);
  releaseTicket();
  await page.waitForFunction(()=>document.getElementById('supportTicketStatus')?.textContent.includes('00000000-0000-0000-0000-000000000009'));
  assert(await page.locator('#supportTicketStatus').isVisible());assert.equal(ticketCalls,2);
  assert.match(await page.locator('#supportTicketStatus').innerText(),/alerte|administration/i);
  await page.evaluate(()=>{activeUser={id:'second'};authListeners.forEach(cb=>cb('SIGNED_IN',{user:activeUser}));});
  assert.equal(await page.locator('#supportTicketText').inputValue(),'');
  assert(!await page.locator('#supportTicketStatus').innerText().then(x=>x.includes('00000000-0000-0000-0000-000000000009')));
  assert.deepEqual(errors,[]);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  console.log('PASS retour d’envoi : texte court prérempli et espaces expliqués, aucune requête invalide, connexion requise visible, progression, échec conservant la saisie, succès visible et même session préservée ; aucun envoi réel.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
