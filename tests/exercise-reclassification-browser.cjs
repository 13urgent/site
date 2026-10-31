// Focused UI contract checks with synthetic shipments and a mocked backend.
const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('assert/strict');
const html=fs.readFileSync(__dirname+'/../tools/site-template.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
const source=fs.readFileSync(__dirname+'/../marketplace.js','utf8');
const action='Classer comme exercice fictif',submit='Confirmer le classement en exercice fictif';

(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  async function setup(options={}){
   const page=await browser.newPage();
   await page.route('**/*',route=>route.abort());
   await page.setContent(html);
   await page.evaluate(options=>{
    window.URGENT_MARKETPLACE_PILOT=true;
    const shipments=['open','assigned','heading_pickup','at_pickup','loaded','delivery_reported','completed','cancelled','archived','exercise'].map(status=>({id:'shipment-'+status,owner_company_id:'owner-synthetic',assigned_company_id:'carrier-synthetic',origin:'Départ fictif '+status,destination:'Arrivée fictive',pickup:'2030-01-01T09:00:00Z',vehicle:'Porteur',pallets:0,weight:0,status:['archived','exercise'].includes(status)?'open':status,is_test:status==='exercise',archived_at:status==='archived'?'2026-10-31T10:00:00Z':null}));
    window.testState={role:'admin',policyInstalled:true,creditedCents:150,shipments,calls:[],signals:[],...options};
    const state=window.testState;
    const profile=()=>({id:'actor-'+state.role,company_id:'owner-synthetic',role:state.role});
    const respond=async(name,args)=>{
     state.calls.push({name,args});
     if(name==='urgent_exercise_reclassification_policy')return state.policyInstalled?{data:{enabled:true,version:'20261031-exercise-reclassification'}}:{error:{message:'Function unavailable'}};
     if(name==='urgent_reclassify_exercise'){
      if(state.classificationError)return{error:{message:state.classificationError}};
      const result=()=>{state.shipments.find(row=>row.id===args.p_shipment).is_test=true;return{data:{reclassified:true,credited_cents:state.creditedCents}}};
      if(state.delayClassification)return new Promise(resolve=>{window.resolveClassification=()=>resolve(result())});
      return result();
     }
     return{data:name==='urgent_shipment_archive_policy'?{enabled:true,restore:true}:{enabled:false}};
    };
    window.sb={auth:{getUser:async()=>({data:{user:{id:profile().id,email:'synthetic@example.com'}}}),onAuthStateChange:callback=>{window.testAuthChange=callback}},rpc:(name,args)=>{
     const request={abortSignal(signal){state.signals.push({name,valid:signal instanceof AbortSignal});return request},then(resolve,reject){return respond(name,args).then(resolve,reject)}};return request;
    },from:table=>{
     const result=()=>({data:table==='profiles'?profile():table==='urgent_business_access'?{registry_checked:true,pilot_enabled:true}:table==='urgent_shipments'?state.shipments:[]});
     const query={select(){return query},eq(){return query},order(){return query},range(){return Promise.resolve(result())},single(){return Promise.resolve(result())},maybeSingle(){return Promise.resolve(result())}};return query;
    }};
   },options);
   await page.addScriptTag({content:source});
   await page.waitForFunction(()=>document.querySelector('#courseCount').textContent.includes('course(s)'));
   return page;
  }
  const card=page=>page.locator('#shipmentTracking > .dossier[data-shipment-id="shipment-open"]');
  async function open(page){await card(page).getByRole('button',{name:action,exact:true}).click();return card(page).locator('.exercise-reclassification-form')}
  async function complete(form){await form.locator('[name=exerciseReason]').fill('  Cette course était uniquement un exercice fictif.  ');await form.locator('[name=confirmExercise]').check()}
  const calls=page=>page.evaluate(()=>testState.calls.filter(call=>call.name==='urgent_reclassify_exercise'));

  for(const role of ['client','carrier']){
   const page=await setup({role});
   assert.equal(await page.getByRole('button',{name:action,exact:true}).count(),0,role+' must not see the admin action');
   await page.close();
  }
  const missing=await setup({policyInstalled:false});
  assert.equal(await missing.getByRole('button',{name:action,exact:true}).count(),4,'Only four eligible statuses');
  await card(missing).getByRole('button',{name:action,exact:true}).click();
  await card(missing).getByRole('status').getByText(/doit encore être activé/).waitFor();
  assert.equal(await card(missing).locator('form.exercise-reclassification-form').count(),0);
  assert.equal((await calls(missing)).length,0);
  await missing.close();

  const page=await setup();
  const form=await open(page);
  assert.equal(await form.locator('[name=exerciseReason]').getAttribute('maxlength'),'1000');
  await form.locator('[name=exerciseReason]').fill('court');
  await form.getByRole('button',{name:submit,exact:true}).click();
  await form.getByRole('status').getByText(/au moins 10 caractères/).waitFor();
  assert.equal((await calls(page)).length,0);
  await form.locator('[name=exerciseReason]').fill('Motif synthétique suffisamment détaillé');
  await form.getByRole('button',{name:submit,exact:true}).click();
  assert.equal((await calls(page)).length,0,'Confirmation is mandatory');
  await complete(form);
  await form.getByRole('button',{name:submit,exact:true}).click();
  await page.locator('#trackingNotice').getByText(/Course classée comme exercice fictif/).waitFor();
  assert.deepEqual((await calls(page))[0].args,{p_shipment:'shipment-open',p_reason:'Cette course était uniquement un exercice fictif.',p_confirm:true});
  const notice=await page.locator('#trackingNotice').textContent();
  assert.match(notice,/1,50\s*€ HT/,'Credit cents must be converted to euros');
  assert.match(notice,/documents déjà enregistrés restent inchangés/);
  assert.match(notice,/nouvelle version.*EXERCICE FICTIF.*PDF/);
  await card(page).getByText('EXERCICE FICTIF — AUCUN TRANSPORT RÉEL',{exact:true}).waitFor();
  assert.equal(await card(page).getByRole('button',{name:action,exact:true}).count(),0);
  assert.equal(await card(page).getByRole('button',{name:'Ranger cet exercice fictif',exact:true}).count(),1);
  assert((await page.evaluate(()=>testState.signals.filter(item=>item.name.includes('exercise')).every(item=>item.valid))));
  await page.close();

  const blocked=await setup({classificationError:'Frais déjà facturés : classement refusé.'});
  const blockedForm=await open(blocked);await complete(blockedForm);
  await blockedForm.getByRole('button',{name:submit,exact:true}).click();
  await blockedForm.getByRole('status').getByText(/Classement non confirmé.*Frais déjà facturés/).waitFor();
  assert.equal(await blockedForm.getByRole('button',{name:submit,exact:true}).isEnabled(),true);
  assert.equal(await blockedForm.locator('[name=confirmExercise]').isChecked(),true);
  assert.equal(await card(blocked).getByText('EXERCICE FICTIF — AUCUN TRANSPORT RÉEL',{exact:true}).count(),0);
  await blocked.close();

  const zero=await setup({creditedCents:0});const zeroForm=await open(zero);await complete(zeroForm);
  await zeroForm.getByRole('button',{name:submit,exact:true}).click();
  await zero.locator('#trackingNotice').getByText(/Aucun crédit de frais supplémentaire/).waitFor();
  await zero.close();

  const changed=await setup({delayClassification:true});const staleForm=await open(changed);await complete(staleForm);
  await staleForm.getByRole('button',{name:submit,exact:true}).click();
  await changed.waitForFunction(()=>typeof window.resolveClassification==='function');
  await changed.evaluate(()=>{testState.role='carrier';testAuthChange()});
  await changed.waitForFunction(()=>!document.querySelector('.exercise-reclassification-form'));
  await changed.evaluate(()=>resolveClassification());
  assert.equal(await changed.getByRole('button',{name:action,exact:true}).count(),0);
  assert(!(await changed.locator('#trackingNotice').textContent()).includes('Course classée'));
  await changed.close();
  console.log('PASS exercise reclassification UI: admin-only eligibility, activation, reason/confirmation, explicit RPC, fee euros, historical PDFs, refresh, refusal and session changes.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
