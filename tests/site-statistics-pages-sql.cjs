const {createDatabase}=require('./helpers/pilot-database.cjs');
const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const {db,actor}=await createDatabase({includeBilling:false});
 try{
  await db.exec('alter table auth.users add column created_at timestamptz not null default now()');
  await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610260001_site_statistics.sql','utf8'));
  const patch=fs.readFileSync(__dirname+'/../supabase/migrations/202611020001_site_statistics_pages.sql','utf8');
  await db.exec(patch);await db.exec(patch);
  const pages=['/','/fonctionnement.html','/courses.html','/mes-courses.html','/deposer.html','/donneurs-ordre.html','/transporteurs.html','/mon-espace.html','/services-chronoss.html','/demenagement.html','/demander-un-devis.html','/retours-a-vide.html','/mobile.html'];
  const record=(page,consent=true)=>db.query("select public.urgent_record_site_event($1,'direct','direct','aucune','page_view',$2)",[page,consent]);
  await db.exec('set role anon');
  assert.equal((await db.query('select public.urgent_site_stats_public_status() s')).rows[0].s.pages_version,'20261102-main-pages');
  for(const page of pages)await record(page);
  for(const page of ['/admin.html','/courses.html?email=private@example.com','/courses.html#secret','/unknown.html',null])await record(page);
  await record('/deposer.html',false);await assert.rejects(db.query('select * from public.urgent_site_events'));
  await db.exec('reset role');
  const count=async()=>Number((await db.query('select count(*) n from public.urgent_site_events')).rows[0].n);
  assert.equal(await count(),pages.length);
  await actor(1);await record('/mon-espace.html');await db.exec('reset role');assert.equal(await count(),pages.length);
  await actor(2);await record('/deposer.html');await db.exec('reset role');assert.equal(await count(),pages.length+1);
  await db.exec('update public.urgent_site_stats_settings set enabled=false');
  await db.exec('set role anon');await record('/courses.html');await db.exec('reset role');assert.equal(await count(),pages.length+1);
  console.log('PASS couverture statistiques : pages métier admises, correctif réexécutable, consentement requis, admin et URL privées exclus, collecte désactivable, tables privées.');
 }finally{await db.close()}
})().catch(e=>{console.error(e);process.exit(1)});
