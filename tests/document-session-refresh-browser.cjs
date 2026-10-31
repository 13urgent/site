// Repeated SIGNED_IN is normal when Supabase revalidates the same browser session.
const {chromium}=require('playwright');
const fs=require('fs'),assert=require('assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const page=await browser.newPage();
  await page.setContent('<body data-site-page="espace"><section id="espace-professionnel"></section></body>');
  await page.evaluate(()=>{
   window.fixtureUser={id:'first-user'};window.authListeners=[];window.savedBranding=[];
   window.sb={auth:{getUser:async()=>({data:{user:fixtureUser}}),onAuthStateChange:cb=>authListeners.push(cb)},
    from:()=>({select(){return this},eq(){return this},single:async()=>({data:{id:fixtureUser.id,company_id:fixtureUser.id+'-company',role:'carrier'}}),maybeSingle:async()=>({data:null})}),
    rpc:async(name,args)=>({data:name==='urgent_transport_dossier_policy'?{enabled:true}:name==='urgent_document_prepare_enabled'?true:name==='urgent_save_document_branding'?(savedBranding.push(args.p_data),1):null})};
  });
  await page.addScriptTag({content:fs.readFileSync(__dirname+'/../transport-dossier.js','utf8')});
  const open=()=>page.getByRole('button',{name:'Mon identité et mon logo pour les documents',exact:true}).click();
  await open();const dialog=page.locator('.transport-dossier-dialog');
  await dialog.locator('[name=address]').fill('Adresse fictive en cours de saisie');
  await page.evaluate(()=>authListeners.forEach(cb=>cb('SIGNED_IN',{user:fixtureUser})));
  assert.equal(await dialog.count(),1,'Repeated sign-in for the same user must keep the document editor open');
  assert.equal(await dialog.locator('[name=address]').inputValue(),'Adresse fictive en cours de saisie');
  await page.evaluate(()=>authListeners.forEach(cb=>cb('TOKEN_REFRESHED',{user:fixtureUser})));
  assert.equal(await dialog.locator('[name=address]').inputValue(),'Adresse fictive en cours de saisie');
  await dialog.getByRole('button',{name:'Enregistrer mon identité et mon logo',exact:true}).click();
  await dialog.getByText('Identité et logo enregistrés pour les prochains documents.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>savedBranding.length),1);
  await page.evaluate(()=>{fixtureUser={id:'second-user'};authListeners.forEach(cb=>cb('SIGNED_IN',{user:fixtureUser}));});
  assert.equal(await dialog.count(),0,'Changing account must clear the previous editor');
  await open();assert.equal(await dialog.locator('[name=address]').inputValue(),'');
  await page.evaluate(()=>{fixtureUser=null;authListeners.forEach(cb=>cb('SIGNED_OUT',null));});
  assert.equal(await dialog.count(),0,'Signing out must clear the editor');
  console.log('PASS session documentaire : même compte et renouvellement préservent la saisie, enregistrement unique, changement de compte et déconnexion effacent les données privées.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
