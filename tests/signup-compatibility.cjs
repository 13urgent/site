const{PGlite}=require('@electric-sql/pglite');const fs=require('fs');const assert=require('assert/strict');
(async()=>{const db=new PGlite();await db.exec(`create schema auth;create table auth.users(id uuid primary key default gen_random_uuid(),email text,raw_user_meta_data jsonb);create table public.companies(id uuid primary key default gen_random_uuid(),name text,company_type text,verification_status text);create table public.profiles(id uuid primary key,company_id uuid,role text);`);await db.exec(fs.readFileSync(__dirname+'/fixtures/create_user_profile.sql','utf8'));await db.exec('create trigger on_auth_user_created after insert on auth.users for each row execute function public.create_user_profile()');await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610170001_business_registration.sql','utf8'));for(const type of ['client','carrier']){const data={requested_account_type:type,account_type:type,company_name:'Entreprise '+type,business_name:'Entreprise '+type,business_siret:'12345678901234',business_use_declared:true};await db.query('insert into auth.users(email,raw_user_meta_data) values($1,$2)',[type+'@example.com',data]);const r=await db.query('select p.role,c.name,c.verification_status from public.profiles p join public.companies c on c.id=p.company_id join auth.users u on u.id=p.id where u.email=$1',[type+'@example.com']);assert.deepEqual(r.rows,[{role:type,name:'Entreprise '+type,verification_status:'pending'}]);}console.log('PASS : fonction réelle exportée + migration SIRET, inscriptions client et transporteur avec entreprise pending');await db.close();await verifyAuthConcurrency()})().catch(e=>{console.error(e);process.exit(1)});

async function verifyAuthConcurrency(){
 const{chromium}=require('playwright');const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const page=await browser.newPage();
  await page.route('http://127.0.0.1:8010/**',route=>{
   const name=new URL(route.request().url()).pathname.split('/').pop()||'index.html';
   return ['index.html','auth.js','config.js','style.css'].includes(name)?route.fulfill({path:__dirname+'/../'+name}):route.fulfill({body:''});
  });
  await page.route('https://cdn.jsdelivr.net/**',route=>route.fulfill({contentType:'application/javascript',body:`
   window.signins=0;window.signups=0;window.otpCalls=0;window.pendingUsers=null;
   window.supabase={createClient:()=>({from:()=>({select(){return this},eq(){return this},maybeSingle:async()=>({data:{role:'client'}})}),auth:{
    onAuthStateChange:()=>{},getUser:()=>{if(window.failUserRead){window.failUserRead=false;return Promise.reject(new Error('network'))}return window.pendingUsers?new Promise(resolve=>pendingUsers.push(resolve)):Promise.resolve({data:{user:null}})},
    signInWithPassword:()=>{signins++;return new Promise((resolve,reject)=>{window.finishSignIn=resolve;window.failSignIn=reject})},
    signUp:async()=>{signups++;return{}},signInWithOtp:()=>{otpCalls++;return new Promise(resolve=>window.finishOtp=resolve)}
   }})};
  `}));
  await page.goto('http://127.0.0.1:8010/index.html');await page.locator('#openAccount').click();
  await page.locator('#authEmail').fill('test@example.com');await page.locator('#authPassword').fill('password-123');
  await page.locator('#signIn').click();await page.waitForFunction(()=>signins===1);
  assert.equal(await page.locator('#signIn').isDisabled(),true);assert.equal(await page.locator('#signUp').isDisabled(),true);assert.equal(await page.locator('#magicLink').isDisabled(),true);
  await page.evaluate(()=>{document.getElementById('signIn').dispatchEvent(new Event('click'));document.getElementById('signUp').dispatchEvent(new Event('click'));});
  assert.deepEqual(await page.evaluate(()=>[signins,signups]),[1,0]);
  await page.evaluate(()=>failSignIn(new Error('network')));await page.waitForFunction(()=>!document.getElementById('signIn').disabled);
  assert.match(await page.locator('#authNotice').textContent(),/Connexion au service impossible/);
  await page.locator('#signIn').click();await page.waitForFunction(()=>signins===2);await page.evaluate(()=>finishSignIn({error:{message:'Identifiants incorrects'}}));
  await page.waitForFunction(()=>!document.getElementById('signIn').disabled);assert.match(await page.locator('#authNotice').textContent(),/Identifiants incorrects/);
  await page.locator('#magicLink').click();await page.waitForFunction(()=>otpCalls===1);
  await page.evaluate(()=>document.getElementById('signIn').dispatchEvent(new Event('click')));assert.equal(await page.evaluate(()=>signins),2);
  await page.evaluate(()=>finishOtp({}));await page.waitForFunction(()=>!document.getElementById('magicLink').disabled);
  await page.locator('#signIn').click();await page.waitForFunction(()=>signins===3);await page.evaluate(()=>{window.failUserRead=true;finishSignIn({});});
  await page.waitForFunction(()=>!document.getElementById('signIn').disabled);assert.match(await page.locator('#authNotice').textContent(),/Connexion effectuée, mais/);
  await page.evaluate(()=>{window.pendingUsers=[];window.firstView=updateAuth();window.secondView=updateAuth();});
  await page.evaluate(async()=>{pendingUsers[1]({data:{user:null}});await secondView;pendingUsers[0]({data:{user:{id:'old-user',email:'old@example.com'}}});await firstView;});
  assert.equal(await page.locator('#accountIdentity').textContent(),'');assert.equal(await page.locator('#signOut').isVisible(),false);
  console.log('PASS auth navigateur : requêtes concurrentes et doubles clics bloqués, erreur réseau/API récupérable, lien magique sérialisé, ancienne lecture de session ignorée');
 }finally{await browser.close();}
}
