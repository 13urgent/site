// Toutes les requêtes Google sont interceptées : aucun test ne crée de conversion réelle.
const {chromium}=require('playwright');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();let googleLoads=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',route=>{
   const u=new URL(route.request().url());
   if(u.hostname!=='site.example'){googleLoads++;return route.fulfill({contentType:'application/javascript',body:''});}
   if(u.pathname==='/google-ads.js')return route.fulfill({contentType:'application/javascript',body:fs.readFileSync(__dirname+'/../google-ads.js','utf8')});
   if(u.pathname==='/audience.css')return route.fulfill({contentType:'text/css',body:fs.readFileSync(__dirname+'/../audience.css','utf8')});
   return route.fulfill({contentType:'text/html; charset=utf-8',body:`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/audience.css"><body ${u.pathname==='/admin.html'?'data-admin-page="true"':''}><main><button onclick="window.serviceWorks=true">Utiliser le service</button></main><footer></footer><script src="/google-ads.js"></script>`});
  });
  const publish=(id='00000000-0000-0000-0000-000000000001',extra={})=>page.evaluate(args=>window.urgentAds.published(args),{id,isTest:false,role:'client',...extra});
  const conversions=()=>page.evaluate(()=>Array.from(window.dataLayer||[],x=>Array.from(x)).filter(x=>x[0]==='event'&&x[1]==='conversion'));
  await page.goto('https://site.example/?email=private@example.com#secret');
  await publish();assert.equal(googleLoads,0);assert.equal((await conversions()).length,0);
  await page.getByRole('button',{name:'Refuser la mesure publicitaire',exact:true}).click();await page.reload();await publish();assert.equal(googleLoads,0);
  // Un accord aux statistiques internes ne vaut jamais accord publicitaire.
  await page.evaluate(()=>localStorage.setItem('13urgent_audience_consent_v1',JSON.stringify({value:'accepted',at:Date.now()})));await page.reload();assert.equal(googleLoads,0);
  await page.getByRole('button',{name:'Gérer la mesure publicitaire'}).click();await page.getByRole('button',{name:'Accepter la mesure publicitaire'}).click();await page.waitForFunction(()=>document.querySelector('script[src*="googletagmanager"]'));
  await publish(undefined,{isTest:true});await publish(undefined,{role:'admin'});await publish(undefined,{role:undefined});await publish('not-a-uuid');assert.equal((await conversions()).length,0);
  await publish();await publish();let events=await conversions();assert.equal(events.length,1);
  assert.deepEqual(events[0][2],{send_to:'AW-18537989618/iTMnCKiasaodEPKLzYdF',value:1,currency:'EUR',transaction_id:'00000000-0000-0000-0000-000000000001',page_location:'https://site.example/',page_referrer:'',page_title:'13 URGENT'});
  const queue=await page.evaluate(()=>Array.from(dataLayer,x=>Array.from(x)));assert(!JSON.stringify(queue).includes('private@example'));assert(!JSON.stringify(queue).includes('secret'));
  assert(queue.some(x=>x[0]==='consent'&&x[1]==='update'&&x[2].ad_personalization==='denied'));
  await page.reload();await publish();assert.equal((await conversions()).length,0);await publish('00000000-0000-0000-0000-000000000002',{role:'carrier'});assert.equal((await conversions()).length,1);
  await page.evaluate(()=>document.cookie='_gcl_aw=test; Path=/');await page.getByRole('button',{name:'Gérer la mesure publicitaire'}).click();await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Retirer mon accord et recharger'}).click()]);
  const loadsAfterWithdrawal=googleLoads;await publish();assert.equal((await conversions()).length,0);assert(!await page.evaluate(()=>document.cookie.includes('_gcl_')));assert.equal(googleLoads,loadsAfterWithdrawal);
  await page.getByRole('button',{name:'Utiliser le service'}).click();assert(await page.evaluate(()=>serviceWorks));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.evaluate(()=>localStorage.setItem('13urgent_ads_consent_v1',JSON.stringify({value:'accepted',at:Date.now()-181*86400000})));await page.reload();assert(await page.locator('#adsChoice').isVisible());assert.equal(googleLoads,loadsAfterWithdrawal);
  await page.goto('https://site.example/admin.html');assert.equal(await page.locator('#adsChoice').count(),0);assert.equal(googleLoads,loadsAfterWithdrawal);
  await context.addInitScript(()=>{Object.defineProperty(navigator,'globalPrivacyControl',{value:true});localStorage.setItem('13urgent_ads_consent_v1',JSON.stringify({value:'accepted',at:Date.now()}));});await page.goto('https://site.example/');await publish();assert.equal(googleLoads,loadsAfterWithdrawal);assert.equal((await conversions()).length,0);
  assert.deepEqual(errors,[]);console.log('PASS Google Ads : consentement distinct, aucun appel avant accord/après refus, GPC, expiration, retrait avec suppression des cookies, doublons et admin/tests exclus, paramètres minimisés et mobile.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
