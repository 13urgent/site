const{chromium}=require('playwright');const assert=require('assert/strict');const fs=require('fs');const path=require('path');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});try{
 const root=process.argv[2]||path.join(__dirname,'..');
 const page=await b.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let role=null;const reads=[];
 await page.route('**/*',r=>{const u=new URL(r.request().url());
  if(u.hostname==='cdn.jsdelivr.net')return r.fulfill({contentType:'application/javascript',body:`window.listeners=[];window.testRole=${JSON.stringify(role)};window.supabase={createClient:()=>({auth:{getUser:async()=>({data:{user:testRole?{id:'user',email:'test@example.com'}:null}}),onAuthStateChange:cb=>listeners.push(cb)},rpc:async()=>({data:{enabled:true,terms_version:'PRO-B2B-2026-10-23-v4',document_url:'conditions-professionnelles-v4.html',terms_accepted:false}}),from:table=>{const q={select(){return q},eq(){return q},in(){return q},order(){return q},limit(){return q},single:async()=>({data:{id:'user',company_id:'company',role:testRole}}),maybeSingle:async()=>({data:{id:'user',company_id:'company',role:testRole}}),then(resolve,reject){return window.readTable(table).then(resolve,reject)}};return q}})};`});
  if(u.pathname==='/rest/v1/rpc/urgent_commercial_status')return r.fulfill({json:{document_url:'conditions-professionnelles-v4.html'}});
  if(u.hostname!=='test.example')return r.abort();const file=path.join(root,u.pathname==='/'?'index.html':u.pathname.slice(1));return fs.existsSync(file)?r.fulfill({path:file}):r.abort();
 });
 await page.exposeFunction('readTable',table=>{reads.push(table);return{data:[]}});
 for(const current of [null,'client','carrier','admin']){
  role=current;reads.length=0;await page.goto('https://test.example/');await page.waitForFunction(()=>window.urgentCommerce?.ready);await page.waitForTimeout(100);
  assert.equal(await page.locator('#adminDialog').count(),0);assert.equal(await page.locator('#commercialAdmin').count(),0);assert.equal(await page.locator('#pilotAccessForm').count(),0);
  assert.equal(await page.locator('#openAdmin').isVisible(),current==='admin');
  if(current==='admin')assert.equal(reads.length,0);
  assert.equal(await page.locator('footer a[data-current-terms]').getAttribute('href'),'conditions-professionnelles-v4.html');
 }
 role='admin';await page.goto('https://test.example/admin.html');await page.locator('#commercialAdmin').waitFor({state:'visible'});await page.locator('#openAdmin').click();await page.locator('#adminDialog').waitFor({state:'visible'});
 await page.evaluate(()=>{testRole=null;listeners.forEach(cb=>cb('SIGNED_OUT',null));});
 await page.waitForFunction(()=>!document.querySelector('#adminDialog').open&&!document.querySelector('#commercialAdmin'));
 assert.equal(await page.locator('#adminDossiers').textContent(),'');
 role='carrier';reads.length=0;await page.goto('https://test.example/admin.html');await page.waitForFunction(()=>document.querySelector('#adminPageNotice').textContent.includes('réservé'));assert.equal(await page.locator('#commercialAdmin').count(),0);assert.equal(await page.locator('#openAdmin').isVisible(),false);
 for(const name of ['mentions-legales.html','confidentialite.html']){await page.goto('https://test.example/'+name);await page.waitForFunction(()=>[...document.querySelectorAll('[data-current-terms]')].every(a=>a.getAttribute('href')==='conditions-professionnelles-v4.html'));}
 await page.goto('https://test.example/conditions-professionnelles.html');await page.waitForURL('**/conditions-professionnelles-v4.html');assert(!(await page.locator('main').textContent()).includes('avant publication'));
 assert(!reads.includes('companies'));assert(!reads.includes('carrier_documents'));assert.deepEqual(errors,[]);
 console.log('PASS séparation : aucun panneau admin sur accueil, lien réservé au rôle serveur, gestion sur page distincte, refus transporteur, effacement après déconnexion, liens contractuels suivant la version serveur.');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
