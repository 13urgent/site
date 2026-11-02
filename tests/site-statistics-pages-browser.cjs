const {chromium}=require('playwright');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const context=await browser.newContext();const page=await context.newPage();let upgraded=false;const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{
   const url=new URL(route.request().url());
   if(url.hostname==='api.example')return route.fulfill({json:{enabled:true,...(upgraded?{pages_version:'20261102-main-pages'}:{})}});
   if(url.pathname==='/audience.js')return route.fulfill({contentType:'application/javascript; charset=utf-8',body:fs.readFileSync(__dirname+'/../audience.js','utf8')});
   return route.fulfill({contentType:'text/html; charset=utf-8',body:`<html><body ${url.pathname==='/admin.html'?'data-admin-page="true"':''}><main></main><footer></footer><script>window.URGENT_SUPABASE_URL='https://api.example';window.URGENT_SUPABASE_PUBLISHABLE_KEY='test-public';window.events=[];const sb={rpc:async(name,args)=>{events.push({name,args});return{data:null}},auth:{onAuthStateChange:()=>{}}};</script><script src="/audience.js"></script></body></html>`});
  });
  await page.goto('https://site.example/courses.html');await page.waitForTimeout(75);assert.equal(await page.locator('#audienceChoice').count(),0);assert.equal(await page.evaluate(()=>events.length),0);
  upgraded=true;await page.reload();await page.getByRole('button',{name:'Accepter les statistiques'}).click();await page.waitForFunction(()=>events.length===1);assert.equal(await page.evaluate(()=>events[0].args.p_page),'/courses.html');
  for(const file of ['deposer.html','mes-courses.html','mon-espace.html','demander-un-devis.html','services-chronoss.html','mobile.html']){
   await page.goto('https://site.example/'+file+'?email=secret@example.com#private');await page.waitForFunction(()=>events.length===1);
   const event=await page.evaluate(()=>events[0]);assert.equal(event.args.p_page,'/'+file);assert(!JSON.stringify(event).includes('secret'));
  }
  await page.getByRole('button',{name:'Gérer les statistiques'}).click();await page.getByRole('button',{name:'Refuser les statistiques'}).click();await page.goto('https://site.example/deposer.html');await page.waitForTimeout(75);assert.equal(await page.evaluate(()=>events.length),0);
  await page.goto('https://site.example/admin.html');await page.waitForTimeout(75);assert.equal(await page.locator('#audienceChoice').count(),0);assert.equal(await page.evaluate(()=>events.length),0);
  assert.deepEqual(errors,[]);console.log('PASS navigateur couverture : compatibilité avant SQL, activation après SQL, parcours métier mesurés uniquement avec accord, paramètres privés absents, refus et administration exclus.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
