const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('assert/strict');
(async()=>{
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
 const p=await b.newPage();
 await p.route('http://127.0.0.1:8010/**',r=>{
  const path=new URL(r.request().url()).pathname;const file=path==='/'?'index.html':path.slice(1);
  if(file.includes('..'))return r.abort();const local=__dirname+'/../'+file;
  return fs.existsSync(local)?r.fulfill({path:local}):r.abort();
 });
 await p.route('https://cdn.jsdelivr.net/**',r=>r.fulfill({contentType:'application/javascript',body:`
 window.reviewCalls=[];window.updateCalls=[];window.sessionExpired=false;window.failUpdate=false;
 window.testDoc={id:'doc-test',company_id:'company-test',document_type:'registration',original_filename:'assurance-test.pdf',review_status:'approved',expires_on:null};
 window.supabase={createClient:()=>({
  auth:{getUser:async()=>({data:{user:sessionExpired?null:{id:'admin-test',email:'test@example.com',user_metadata:{}}}}),onAuthStateChange:()=>{}},
  rpc:async(name,args)=>{
   if(name==='urgent_pilot_directory')return{data:[{company_id:'company-test',pilot_enabled:true,carrier_ready:false}]};
   if(name==='urgent_commercial_status')return{data:{enabled:false,terms_version:'PRO-B2B-2026-10-20-v3',terms_accepted:false}};
   if(name==='urgent_correct_document'){reviewCalls.push({name,args});Object.assign(testDoc,{document_type:args.p_kind,expires_on:args.p_expiry,review_status:'pending'});return{};}
   return{data:null};
  },
  from:table=>{const q={select(){return q},eq(){return q},in(){return q},
   update(values){return{eq:(key,id)=>({select:()=>({single:async()=>{updateCalls.push({values,key,id});if(failUpdate)throw Error('Connexion interrompue');Object.assign(testDoc,values);return{data:{id}};}})})}},
   maybeSingle:async()=>({data:{id:'admin-test',company_id:'admin-company',role:'admin'}}),
   order:async()=>({data:table==='companies'?[{id:'company-test',name:'Test transporteur',verification_status:'pending'}]:[{...testDoc}]})};return q;}
 })};`}));
 const errors=[];p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 await p.goto('http://127.0.0.1:8010/admin.html');await p.evaluate(()=>{window.validationMails=[];window.urgentSupport={reviewDocument:()=>{},notifyBusinessValidation:async(companyId,pending)=>{validationMails.push({companyId,pending});return{notified:true,eligible:false,recipient_emails:['carrier@example.com']}}};});await p.locator('#openAdmin').click();await p.getByRole('button',{name:'Notifier la décision au transporteur',exact:true}).click();await p.waitForFunction(()=>validationMails.length===1&&document.querySelector('#adminDossiers').textContent.includes('accepté la notification à carrier@example.com'));assert.deepEqual(await p.evaluate(()=>validationMails),[{companyId:'company-test',pending:true}]);assert.equal(await p.evaluate(()=>updateCalls.length),0);
 const revoke=p.getByRole('button',{name:'Retirer l’approbation',exact:true});
 await revoke.waitFor();assert.match(await p.locator('#adminDossiers').textContent(),/Autorisation de l’établissement : accordée/);assert.match(await p.locator('#adminDossiers').textContent(),/Catégories manquantes.*marchandises/);await p.evaluate(()=>sessionExpired=true);await revoke.click();
 await p.waitForFunction(()=>document.getElementById('adminNotice').textContent.includes('Session administrateur expirée'));
 assert.equal(await revoke.isEnabled(),true);assert.equal(await p.evaluate(()=>updateCalls.length),0);
 await p.evaluate(()=>{sessionExpired=false;failUpdate=true});await revoke.click();
 await p.waitForFunction(()=>document.getElementById('adminNotice').textContent.includes('Connexion interrompue'));
 assert.equal(await revoke.isEnabled(),true);
 await p.evaluate(()=>failUpdate=false);await revoke.click();
 await p.waitForFunction(()=>document.getElementById('adminNotice').textContent.includes('Approbation retirée'));
 assert.equal(await p.evaluate(()=>testDoc.review_status),'rejected');
 const update=await p.evaluate(()=>updateCalls.at(-1));
 assert.equal(update.values.review_status,'rejected');assert.equal(update.values.reviewed_by,'admin-test');assert.equal(update.id,'doc-test');
 await p.getByRole('button',{name:'Corriger la catégorie / la date'}).click();
 await p.locator('.document-correction select').selectOption('insurance_rc');await p.locator('.document-correction input[type=date]').fill('2027-09-22');
 await p.getByRole('button',{name:'Enregistrer la correction',exact:true}).click();
 await p.waitForFunction(()=>document.getElementById('adminNotice').textContent.includes('Correction enregistrée'));
 assert.deepEqual(await p.evaluate(()=>reviewCalls[0]),{name:'urgent_correct_document',args:{p_document:'doc-test',p_kind:'insurance_rc',p_expiry:'2027-09-22'}});
 assert.ok((await p.locator('#adminDossiers').innerText()).includes('pending'));
 await p.getByRole('button',{name:'Accepter',exact:true}).click();
 await p.waitForFunction(()=>document.getElementById('adminNotice').textContent.includes('Document accepté'));
 assert.equal(await p.evaluate(()=>testDoc.review_status),'approved');assert.equal(await revoke.count(),1);
 assert.deepEqual(errors,[]);
 console.log('PASS documents : révocation d’approbation, session expirée sans écriture, erreur réseau et bouton réactivé, correction et nouvelle approbation');
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exit(1)});
