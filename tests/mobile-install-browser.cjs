const{chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');const assert=require('assert/strict');
(async()=>{
 const root=path.resolve(process.argv[2]||path.join(__dirname,'..'));const server=http.createServer((req,res)=>{
  const name=new URL(req.url,'http://localhost').pathname;
  if(name.startsWith('/rest/')){res.writeHead(200,{'Content-Type':'application/json'});return res.end('{"private":"fixture-not-to-cache"}');}
  const local=path.join(root,name==='/'?'mobile.html':name);if(!local.startsWith(root+path.sep)||!fs.existsSync(local)||!fs.statSync(local).isFile()){res.writeHead(404);return res.end();}
  const types={'.js':'application/javascript','.css':'text/css','.html':'text/html','.webmanifest':'application/manifest+json','.png':'image/png','.svg':'image/svg+xml'};res.writeHead(200,{'Content-Type':types[path.extname(local)]||'text/plain'});res.end(fs.readFileSync(local));
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin='http://127.0.0.1:'+server.address().port;
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const context=await b.newContext({viewport:{width:390,height:844}});const p=await context.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
  await context.route('https://**/*',r=>r.request().url().includes('cdn.jsdelivr.net')?r.fulfill({contentType:'application/javascript',body:`window.recovery=[];window.supabase={createClient:()=>({auth:{getUser:async()=>({data:{user:null}}),onAuthStateChange:()=>{},resetPasswordForEmail:async(email,options)=>{recovery.push(options.redirectTo);return{};}},rpc:async()=>({data:null})})};`}):r.fulfill({contentType:'application/json',body:'{"enabled":false}'}));
  await p.goto(origin+'/mobile.html');await p.waitForFunction(()=>navigator.serviceWorker.controller!==null);
  const manifest=await p.evaluate(async()=>await(await fetch('mobile.webmanifest')).json());assert.equal(manifest.display,'standalone');assert.equal(manifest.start_url,'mobile.html');
  await p.locator('#openAccount').click();await p.locator('#authEmail').fill('controlled-test@example.com');await p.locator('#magicLink').click();await p.waitForFunction(()=>recovery.length===1);assert.equal(await p.evaluate(()=>recovery[0]),origin+'/mobile.html');await p.locator('#closeAccount').click();
  await p.evaluate(async()=>{await fetch('/rest/v1/private');await fetch('/mobile.html?code=private-test-code');});
  const urls=await p.evaluate(async()=>{const all=[];for(const n of await caches.keys())for(const r of await(await caches.open(n)).keys())all.push(r.url);return all;});assert(urls.some(u=>u.endsWith('/mobile.html')));assert(!urls.some(u=>u.includes('/rest/')||u.includes('/storage/')||u.includes('code=')||u.includes('supabase.co')));
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.equal(await p.locator('.mobile-tabs').isVisible(),true);await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await p.screenshot({path:'/workspace/13urgent-tools/application-accueil-20261029.png'});
  await context.setOffline(true);await p.reload({waitUntil:'domcontentloaded'});await p.locator('#mobileOffline').waitFor({state:'visible'});assert.equal(await p.locator('.mobile-tabs').isVisible(),true);assert.deepEqual(errors,[]);
  console.log('PASS installation navigateur : vrai service worker actif sur serveur local, manifeste et cache chargés, retour mot de passe vers l’app, aucune réponse privée/code Auth en cache, coque accessible hors connexion et mobile sans débordement.');
 }finally{await b.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exit(1)});
