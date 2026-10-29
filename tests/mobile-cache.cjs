const vm=require('vm');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const hooks={},written=[],removed=[],saved=new Map();let offline=false,installed=[];
 const cache={addAll:async rows=>installed=rows,put:async(req,response)=>{written.push(req.url);saved.set(req.url,response);},match:async key=>saved.get(key)};
 const scope={URL,Request,Response,Set,console,self:{registration:{scope:'https://13urgent.fr/'},location:{origin:'https://13urgent.fr'},clients:{claim:async()=>{}},addEventListener:(name,fn)=>hooks[name]=fn},caches:{open:async()=>cache,keys:async()=>['another-app','13urgent-mobile-old'],delete:async name=>removed.push(name)},fetch:async()=>{if(offline)throw Error('offline');return new Response('static',{status:200});}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/../mobile-sw.js','utf8'),scope);
 let wait;hooks.install({waitUntil:p=>wait=p});await wait;assert(installed.includes('mobile.html'));assert(!installed.some(x=>x.includes('admin.html')||x.includes('/rest/')||x.includes('urgent-mission-files')));
 hooks.activate({waitUntil:p=>wait=p});await wait;assert.deepEqual(removed,['13urgent-mobile-old']);
 function request(url,method='GET'){let answer=null;hooks.fetch({request:new Request(url,{method}),respondWith:p=>answer=p});return answer;}
 for(const url of['https://example.supabase.co/rest/v1/profiles','https://example.supabase.co/auth/v1/token','https://example.supabase.co/storage/v1/object/sign/urgent-mission-files/private.pdf?token=secret','https://waze.com/ul?q=private','https://13urgent.fr/admin.html','https://13urgent.fr/mobile.html?code=private-auth-code'])assert.equal(request(url),null);
 assert.equal(request('https://13urgent.fr/mobile.html','POST'),null);
 assert.equal((await request('https://13urgent.fr/mobile.html')).status,200);assert.deepEqual(written,['https://13urgent.fr/mobile.html']);offline=true;assert.equal(await(await request('https://13urgent.fr/mobile.html')).text(),'static');assert.equal((await request('https://13urgent.fr/mobile.css')).status,503);
 const manifest=JSON.parse(fs.readFileSync(__dirname+'/../mobile.webmanifest'));assert.equal(manifest.display,'standalone');assert.equal(manifest.start_url,'mobile.html');for(const icon of manifest.icons)assert(fs.existsSync(__dirname+'/../'+icon.src));
 console.log('PASS PWA : manifeste et icônes disponibles, cache statique seul, API/Auth/pièces privées/GPS/code de connexion exclus, aucun POST mis en cache, repli hors ligne et caches étrangers préservés.');
})().catch(e=>{console.error(e);process.exit(1)});
