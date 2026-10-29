const{chromium}=require('playwright');const fs=require('fs');const path=require('path');const assert=require('assert/strict');
(async()=>{
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  for(const enabled of[true,false]){
   const p=await b.newPage({viewport:{width:390,height:844}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
   await p.route('https://cdn.jsdelivr.net/**',r=>r.fulfill({contentType:'application/javascript',body:`
window.testDocs=[];window.testUploads=[];
window.supabase={createClient:()=>({auth:{getUser:async()=>({data:{user:{id:'client-test',email:'client@example.com',user_metadata:{}}}}),onAuthStateChange:()=>{}},rpc:async(name)=>({data:name==='urgent_document_alert_policy'?{enabled:true,client_upload:${enabled}}:null}),storage:{from:()=>({upload:async(name,file)=>{testUploads.push(name);return{};}})},from:table=>{
 const rows=()=>table==='carrier_documents'?testDocs:[];
 const q={select(){return q},eq(){return q},order(){return q},in(){return q},range:async()=>({data:rows()}),then(resolve){return Promise.resolve({data:rows()}).then(resolve)},maybeSingle:async()=>({data:table==='profiles'?{id:'client-test',company_id:'client-company',role:'client'}:null}),single:async()=>({data:{id:'client-company',name:'Client test',verification_status:'pending'}}),insert:async(row)=>{testDocs.push({...row,id:'doc-'+testDocs.length,created_at:new Date().toISOString()});return{};}};return q;}})};`}));
   await p.route('http://127.0.0.1:8010/**',r=>{const u=new URL(r.request().url());const file=path.join(__dirname,'..',u.pathname==='/'?'index.html':u.pathname);return fs.existsSync(file)?r.fulfill({path:file}):r.abort();});
   await p.goto('http://127.0.0.1:8010/');await p.waitForFunction(()=>window.refreshProfessionalAccess!==undefined);await p.evaluate(()=>refreshProfessionalAccess());
   if(!enabled){assert.equal(await p.locator('#openDocuments').isVisible(),false);await p.close();continue;}
   await p.locator('#openDocuments').click();await p.locator('#companyStatus').getByText(/Client test/).waitFor();
   assert.equal(await p.locator('#documentsDialog .eyebrow').textContent(),'ESPACE DONNEUR D’ORDRE');assert.equal(await p.locator('#documentType option:enabled').count(),1);
   assert.equal(await p.locator('#documentType').inputValue(),'registration');assert(!(await p.locator('#documentsDialog').textContent()).includes('Aucune proposition ne sera autorisée'));
   let expected=0;for(const name of['kbis-1.pdf','kbis-2.pdf']){
    await p.locator('#documentFile').setInputFiles({name,mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nDocument de test')});
    await p.locator('#documentForm button[type=submit]').click();await p.waitForFunction(n=>testDocs.length===n,++expected);await p.waitForFunction(()=>!document.querySelector('#documentForm button[type=submit]').disabled&&!document.querySelector('#documentNotice').hidden);
   }
   assert.equal(await p.evaluate(()=>testDocs.length),2);assert.equal(await p.evaluate(()=>testUploads.length),2);assert.equal(await p.evaluate(()=>testDocs.every(d=>d.review_status==='pending'&&d.document_type==='registration'&&d.company_id==='client-company')),true);
   assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);await p.close();
  }
  console.log('PASS documents donneur d’ordre : activation serveur requise, Kbis seul, deux dépôts conservés en attente, aucune exigence transporteur, mobile et absence d’erreur JavaScript.');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1)});
