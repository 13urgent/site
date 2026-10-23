const{chromium}=require('playwright');const fs=require('fs');const assert=require('assert/strict');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});const p=await b.newPage();await p.route('http://127.0.0.1:8010/**',r=>{const path=new URL(r.request().url()).pathname;const name=path==='/'?'index.html':path.slice(1);if(name.includes('..'))return r.abort();const file=__dirname+'/../'+name;if(!fs.existsSync(file))return r.abort();return r.fulfill({path:file});});await p.route('https://cdn.jsdelivr.net/**',r=>r.fulfill({contentType:'application/javascript',body:`window.activeUser={id:'carrier-test',email:'test@example.com',user_metadata:{}};window.authListeners=[];window.deferCompany=false;window.companyRelease=null;window.deferUpload=false;window.deferInsert=false;window.uploadRelease=null;window.insertRelease=null;window.insertCalls=0;window.supabase={createClient:()=>({auth:{getUser:async()=>({data:{user:activeUser}}),onAuthStateChange:f=>{authListeners.push(f)}},storage:{from:()=>({upload:async()=>{if(deferUpload)await new Promise(resolve=>uploadRelease=resolve);return{};}})},from:table=>{const q={insert:async()=>{insertCalls++;if(deferInsert)await new Promise(resolve=>insertRelease=resolve);return{};},select(){return q},eq(){return q},maybeSingle:async()=>({data:{id:'carrier-test',company_id:'company-test',role:'carrier'}}),single:async()=>{if(deferCompany)await new Promise(resolve=>companyRelease=resolve);return {data:{id:'company-test',name:'Entreprise test',verification_status:'pending'}}},order:async()=>({data:[{id:'doc-test',original_filename:'document-prive-test.pdf',document_type:'registration',review_status:'pending'}]})};return q;}})};`}));await p.goto('http://127.0.0.1:8010/');await p.locator('#openDocuments').click();await p.waitForFunction(()=>document.querySelector('#myDocuments').textContent.includes('document-prive-test.pdf'));await p.evaluate(()=>{activeUser=null;authListeners.forEach(f=>f('SIGNED_OUT',null))});await p.waitForFunction(()=>!document.getElementById('documentsDialog').open);assert.equal(await p.locator('#myDocuments').innerText(),'');assert.equal(await p.locator('#companyStatus').innerText(),'');
await p.evaluate(()=>{activeUser={id:'carrier-test',email:'test@example.com',user_metadata:{}};authListeners.forEach(f=>f('SIGNED_IN',{user:activeUser}))});
await p.waitForFunction(()=>!document.getElementById('openDocuments').hidden);
await p.evaluate(()=>deferCompany=true);await p.locator('#openDocuments').click();await p.waitForFunction(()=>typeof companyRelease==='function');
await p.evaluate(()=>{activeUser=null;authListeners.forEach(f=>f('SIGNED_OUT',null))});
await p.waitForFunction(()=>!document.getElementById('documentsDialog').open);
await p.evaluate(()=>companyRelease());await p.waitForTimeout(30);
assert.equal(await p.locator('#companyStatus').textContent(),'');assert.equal(await p.locator('#myDocuments').textContent(),'');
for(const stage of ['upload','insert']){
 await p.evaluate(stage=>{deferCompany=false;deferUpload=stage==='upload';deferInsert=stage==='insert';uploadRelease=null;insertRelease=null;activeUser={id:'carrier-test',email:'test@example.com',user_metadata:{}};authListeners.forEach(f=>f('SIGNED_IN',{user:activeUser}));},stage);
 await p.waitForFunction(()=>!document.getElementById('openDocuments').hidden);await p.locator('#openDocuments').click();
 await p.locator('#documentFile').setInputFiles({name:'private-renewal.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 test')});
 await p.getByRole('button',{name:'Envoyer pour validation'}).click();
 await p.waitForFunction(stage=>typeof window[stage+'Release']==='function',stage);
 await p.evaluate(()=>{activeUser=null;authListeners.forEach(f=>f('SIGNED_OUT',null));});
 await p.waitForFunction(()=>!document.getElementById('documentsDialog').open);
 await p.evaluate(stage=>window[stage+'Release'](),stage);await p.waitForTimeout(30);
 assert.equal(await p.locator('#documentsDialog').evaluate(e=>e.open),false);
 assert.equal(await p.locator('#documentNotice').textContent(),'');assert.equal(await p.locator('#companyStatus').textContent(),'');
 assert.equal(await p.locator('#documentForm button[type=submit]').isEnabled(),true);
 if(stage==='upload')assert.equal(await p.evaluate(()=>insertCalls),0);
}
assert.ok((await p.locator('#documentRenewalWarning').textContent()).includes('suspendues'));console.log('PASS : contenu privé effacé à la déconnexion, réponses entreprise et envoi tardives ignorées, aucune fiche créée après déconnexion, avertissement renouvellement');await b.close()})().catch(e=>{console.error(e);process.exit(1)});
