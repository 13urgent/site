// Reproduit l'incident sans contacter Supabase ni envoyer d'e-mail réel.
const{chromium}=require('playwright');const fs=require('fs');const assert=require('assert/strict');
(async()=>{const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});try{
 const p=await browser.newPage({viewport:{width:390,height:844}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.route('http://site.example/**',r=>{const file=new URL(r.request().url()).pathname.split('/').pop()||'index.html';return ['index.html','auth.js','style.css','config.js'].includes(file)?r.fulfill({path:__dirname+'/../'+file}):r.fulfill({body:''});});
 await p.route('https://cdn.jsdelivr.net/**',r=>r.fulfill({contentType:'application/javascript',body:`
 window.otpCalls=[];window.signups=[];window.otpError={code:'otp_disabled',message:'Signups not allowed for otp'};
 window.supabase={createClient:()=>({from:()=>({select(){return this},eq(){return this},maybeSingle:async()=>({data:{role:'client'}})}),auth:{
 getUser:async()=>({data:{user:null}}),onAuthStateChange:()=>{},
 resetPasswordForEmail:async (email,options)=>{otpCalls.push({email,options});return{error:otpError}},
 signUp:async args=>{signups.push(args);return{data:{user:{id:'local-test'},session:null},error:null}}
 }})};
 `}));
 await p.goto('http://site.example/?utm_source=google#deposer');await p.locator('#openAccount').click();
 assert.match(await p.locator('#registrationAction').innerText(),/Première visite/);
 assert.match(await p.locator('#loginActions').innerText(),/Mot de passe oublié/);
 await p.locator('#authEmail').fill('nouveau@example.com');await p.locator('#magicLink').click();
 await p.waitForFunction(()=>!document.getElementById('magicLink').disabled);
 assert.match(await p.locator('#authNotice').innerText(),/n’a pas pu être envoyé/);
 assert.doesNotMatch(await p.locator('#authNotice').innerText(),/Signups|otp|Envoi impossible/);
 assert.equal(await p.evaluate(()=>signups.length),0);
 assert.deepEqual(await p.evaluate(()=>otpCalls[0]),{email:'nouveau@example.com',options:{redirectTo:'http://site.example'}});
 // Le même visiteur peut ensuite s'inscrire sans perdre son adresse.
 await p.locator('#authPassword').fill('mot-de-passe-test');await p.locator('#businessName').fill('Entreprise locale test');await p.locator('#businessSiret').fill('12345678901234');await p.locator('#businessUse').check();await p.locator('#signUp').click();
 await p.waitForFunction(()=>signups.length===1&&!document.getElementById('signUp').disabled);
 const registration=await p.evaluate(()=>signups[0]);assert.equal(registration.email,'nouveau@example.com');assert.equal(registration.options.data.requested_account_type,'client');assert.equal(registration.options.data.business_siret,'12345678901234');assert.equal(registration.options.data.business_use_declared,true);assert.equal(registration.options.data.role,undefined);
 assert.match(await p.locator('#authNotice').innerText(),/Inscription enregistrée/);
 // Les comptes existants gardent la connexion par lien ; succès et erreur réseau restent honnêtes.
 await p.evaluate(()=>otpError=null);await p.locator('#magicLink').click();await p.waitForFunction(()=>!document.getElementById('magicLink').disabled);assert.match(await p.locator('#authNotice').innerText(),/recevrez un e-mail pour réinitialiser/);
 await p.evaluate(()=>otpError={status:429,message:'raw server detail'});await p.locator('#magicLink').click();await p.waitForFunction(()=>!document.getElementById('magicLink').disabled);assert.match(await p.locator('#authNotice').innerText(),/Patientez/);
 await p.evaluate(()=>otpError={message:'unexpected secret technical response'});await p.locator('#magicLink').click();await p.waitForFunction(()=>!document.getElementById('magicLink').disabled);assert.doesNotMatch(await p.locator('#authNotice').innerText(),/unexpected|secret technical/);assert.match(await p.locator('#authNotice').innerText(),/n’a pas pu être envoyé/);
 assert.equal(await p.evaluate(()=>signups.length),1);assert.equal(await p.locator('#authEmail').inputValue(),'nouveau@example.com');assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
 console.log('PASS réinitialisation : API recovery dédiée sans création de compte, erreurs sans détails techniques, confirmation conditionnelle, inscription préservée et mobile.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
