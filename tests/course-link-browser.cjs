// Real local HTTP pages; fixture backend only. No account or production write.
const {chromium}=require('playwright');
const http=require('node:http');const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');

(async()=>{
 const root=path.resolve(__dirname,'..');
 const server=http.createServer((req,res)=>{
  const pathname=new URL(req.url,'http://localhost').pathname;
  const file=path.resolve(root,'.'+pathname);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
  const ext=path.extname(file);res.setHeader('Content-Type',ext==='.js'?'application/javascript':ext==='.css'?'text/css':ext==='.html'?'text/html':'application/octet-stream');res.end(fs.readFileSync(file));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const id='c4fdab01-dfd5-49d5-9a60-39ab80abc001';
 let mode='open',signedIn=true;
 const errors=[];
 try{
  const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(u.hostname==='cdn.jsdelivr.net')return route.fulfill({contentType:'application/javascript',body:`
    window.fixtureSignedIn=${signedIn};window.fixtureMode=${JSON.stringify(mode)};window.fixtureCallbacks=[];window.fixtureReads=[];window.fixtureWrites=[];
    const fixtureUser={id:'fixture-user',email:'test@example.invalid'};
    const fixtureShipment={id:${JSON.stringify(id)},origin:'Ville test A',destination:'Ville test B',pickup:new Date(Date.now()+86400000).toISOString(),vehicle:'VL / fourgon',pallets:3,weight:525,status:fixtureMode==='closed'?'assigned':'open',is_test:fixtureMode==='test',archived_at:fixtureMode==='archived'?new Date().toISOString():null,owner_company_id:'other-company',revision:0};
    const fixtureData=table=>table==='urgent_shipments'?(fixtureMode==='missing'?[]:[fixtureShipment]):[];
    window.supabase={createClient:()=>({auth:{getUser:async()=>{if(!window.fixtureFiltersApplied&&document.getElementById('courseSearch')){document.getElementById('courseSearch').value='filtre initial sans résultat';document.getElementById('courseVehicle').value='Porteur';window.fixtureFiltersApplied=true;}await new Promise(r=>setTimeout(r,10));return{data:{user:fixtureSignedIn?fixtureUser:null}}},getSession:async()=>({data:{session:fixtureSignedIn?{user:fixtureUser}:null}}),onAuthStateChange:cb=>{fixtureCallbacks.push(cb);return{data:{subscription:{unsubscribe(){}}}}},signOut:async()=>{fixtureSignedIn=false;return{}}},rpc:async(name,args)=>{fixtureReads.push('rpc:'+name);return{data:{enabled:false}}},from:table=>{fixtureReads.push(table);const q={select(){return q},eq(){return q},in(){return q},order(){return q},limit(){return q},range(){return q},single:async()=>({data:table==='profiles'?{id:'fixture-user',company_id:'fixture-company',role:'carrier'}:null}),maybeSingle:async()=>({data:table==='profiles'?{id:'fixture-user',company_id:'fixture-company',role:'carrier'}:table==='urgent_business_access'?{registry_checked:true,pilot_enabled:true}:null}),then(resolve,reject){return Promise.resolve({data:fixtureData(table)}).then(resolve,reject)}};return q}})};
   `});
   if(u.origin!==base)return route.abort();
   if(u.pathname==='/config.js')return route.fulfill({contentType:'application/javascript',body:fs.readFileSync(path.join(root,'config.js'),'utf8')+'\nwindow.URGENT_MARKETPLACE_PILOT=true;'});
   return route.continue();
  });
  await page.goto(base+'/courses.html?course='+id);
  await page.locator('.shipment-linked').waitFor();
  assert.equal(await page.locator('#courseSearch').inputValue(),'');
  assert.equal(await page.locator('#courseVehicle').inputValue(),'');
  assert.equal(await page.locator('.shipment-linked').getAttribute('data-shipment-id'),id);
  assert.equal(await page.evaluate(()=>document.activeElement?.dataset.shipmentId),id);
  assert.match(await page.locator('#courseLinkNotice').textContent(),/correspondant à ce lien est affichée/);
  assert.equal(await page.locator('.shipment-linked').evaluate(e=>e.style.outline.includes('3px')),true);
  await page.locator('#courseSearch').fill('aucune correspondance');
  assert.equal(await page.locator('#courseSearch').inputValue(),'aucune correspondance');
  await page.getByRole('button',{name:'Actualiser les courses et le suivi',exact:true}).click();
  await page.locator('#courseLinkNotice').getByText(/masquée par les filtres/).waitFor();
  assert.equal(await page.locator('#courseSearch').inputValue(),'aucune correspondance');

  signedIn=false;await page.goto(base+'/courses.html?course='+id);
  const signIn=page.getByRole('button',{name:'Se connecter pour consulter cette demande',exact:true});
  await signIn.waitFor();assert.equal(await page.locator('#shipments .shipment').count(),0);
  assert.equal(await page.evaluate(()=>fixtureReads.includes('urgent_shipments')),false);
  await signIn.click();await page.locator('#accountDialog').waitFor({state:'visible'});
  assert.equal(new URL(page.url()).searchParams.get('course'),id);
  await page.evaluate(()=>{document.querySelector('#accountDialog').close();fixtureSignedIn=true;for(const cb of fixtureCallbacks)cb('SIGNED_IN',{user:{id:'fixture-user',email:'test@example.invalid'}});});
  await page.locator('.shipment-linked').waitFor();
  assert.equal(new URL(page.url()).searchParams.get('course'),id);

  signedIn=true;
  for(mode of ['missing','closed','test','archived']){
   await page.goto(base+'/courses.html?course='+id);
   await page.locator('#courseLinkNotice').getByText('Cette demande n’est pas disponible pour votre compte ou n’est plus ouverte.',{exact:true}).waitFor();
   assert.equal(await page.locator('.shipment-linked').count(),0);
   assert.equal(await page.locator('#courseLinkNotice').textContent().then(t=>t.includes('Ville test')),false);
  }
  mode='open';await page.goto(base+'/courses.html?course='+encodeURIComponent('<script>alert(1)</script>'));
  await page.locator('#courseCount').getByText(/course\(s\) ouverte/).waitFor();
  assert.equal(await page.locator('#courseLinkNotice').isVisible(),false);
  assert.equal(await page.locator('.shipment-linked').count(),0);
  assert.deepEqual(await page.evaluate(()=>fixtureWrites),[]);
  assert.deepEqual(errors,[]);
  console.log('PASS course links: authenticated matching and focus, query preserved through sign-in, filters retained after initial load, missing/closed/test/archived generic, invalid parameter ignored; no production writes.');
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exit(1)});
