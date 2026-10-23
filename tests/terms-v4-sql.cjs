const {createDatabase,uid}=require('./helpers/pilot-database.cjs');
const assert=require('assert/strict');const fs=require('fs');const crypto=require('crypto');
(async()=>{
 const {db,actor}=await createDatabase({includeBilling:false});
 try{
  await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610200001_manual_commerce.sql','utf8'));
  await db.query("update public.urgent_business_access set plan='basics' where company_id=$1",[uid(3)]);
  await actor(1);await db.query("select public.urgent_set_commercial_mode(true,'CHRONOSS - VIREMENTS ET FACTURATION MANUELLE')");
  await actor(3);await db.query("select public.urgent_accept_terms('PRO-B2B-2026-10-20-v3')");
  const status=async()=>(await db.query('select public.urgent_commercial_status() s')).rows[0].s;
  assert.equal((await status()).terms_accepted,true);
  assert.equal((await db.query('select public.urgent_carrier_ready($1) ready',[uid(3)])).rows[0].ready,true);
  await db.exec('reset role');
  const migration=fs.readFileSync(__dirname+'/../supabase/migrations/202610230006_terms_v4.sql','utf8');
  await db.exec(migration);await db.exec(migration);
  await actor(3);const current=await status();
  assert.equal(current.enabled,true);assert.equal(current.terms_accepted,false);
  assert.equal(current.document_url,'conditions-professionnelles-v4.html');
  assert.equal(current.document_sha256,crypto.createHash('sha256').update(fs.readFileSync(__dirname+'/../conditions-professionnelles-v4.html')).digest('hex'));
  assert.equal((await db.query('select public.urgent_carrier_ready($1) ready',[uid(3)])).rows[0].ready,false);
  await assert.rejects(db.query("select public.urgent_accept_terms('PRO-B2B-2026-10-20-v3')"),/non actuelle/);
  await db.query("select public.urgent_accept_terms('PRO-B2B-2026-10-23-v4')");
  assert.equal((await status()).terms_accepted,true);
  assert.equal((await db.query('select public.urgent_carrier_ready($1) ready',[uid(3)])).rows[0].ready,true);
  await db.exec('reset role');
  assert.equal((await db.query('select count(*)::int n from public.urgent_terms_acceptances')).rows[0].n,2);
  console.log('PASS conditions v4 : activation réexécutable, empreinte exacte, mode commercial conservé, v3 archivée, nouvelle acceptation obligatoire avant rétablissement des offres.');
 }finally{await db.close()}
})().catch(e=>{console.error(e);process.exit(1)});
